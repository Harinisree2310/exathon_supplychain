"""
Exasol connection management.

Design decisions:
- pyexasol is the official Exasol Python driver (WebSocket-based, no ODBC).
- Connection pooling is kept simple: one connection per request lifecycle.
- Silent fallback to SQLite or in-memory calculation is explicitly forbidden.
- Connections open without requiring the application schema to already exist,
  then OPEN SCHEMA after CREATE SCHEMA IF NOT EXISTS during init.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from enum import Enum
from typing import Any, Generator

import pandas as pd
import pyexasol  # type: ignore

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseStatus(str, Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    UNCHECKED = "unchecked"


class ExasolUnavailableError(RuntimeError):
    """Raised when no Exasol connection is available.

    Never silently replaced with in-memory fallback.
    """


def _connection_error_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [OSError, ConnectionError, TimeoutError]
    for name in (
        "ExaConnectionError",
        "ExaCommunicationError",
        "ExaConnectionFailedError",
    ):
        cls = getattr(pyexasol, name, None)
        if isinstance(cls, type):
            types.append(cls)
    return tuple(types)


def _make_connection() -> pyexasol.ExaConnection:
    """Open a pyexasol connection. Schema is opened separately so first-run init works."""
    settings = get_settings()
    return pyexasol.connect(
        dsn=settings.exasol_dsn,
        user=settings.exasol_user,
        password=settings.exasol_password,
        compression=True,
        websocket_sslopt={"check_hostname": False, "cert_reqs": 0},
    )


def import_dataframe(
    conn: pyexasol.ExaConnection,
    dataframe: pd.DataFrame,
    table_name: str,
) -> Any:
    """Import supplied columns over TLS without verifying PyExasol's ephemeral certificate."""
    original_execute = conn.execute

    def execute_import_with_certificate_override(
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> Any:
        normalized_query = query.lstrip().upper()
        if normalized_query.startswith("IMPORT INTO ") and "AT 'HTTPS://" in normalized_query:
            query = f"{query.rstrip().rstrip(';')}\nIGNORE CERTIFICATE"
        if query_params is None:
            return original_execute(query)
        return original_execute(query, query_params)

    setattr(conn, "execute", execute_import_with_certificate_override)
    try:
        return conn.import_from_pandas(
            dataframe,
            table_name,
            import_params={"columns": list(dataframe.columns)},
        )
    finally:
        setattr(conn, "execute", original_execute)


def _open_schema(conn: pyexasol.ExaConnection) -> None:
    settings = get_settings()
    schema = "".join(ch for ch in settings.exasol_schema if ch.isalnum() or ch == "_").upper()
    try:
        conn.execute(f"OPEN SCHEMA {schema}")
    except Exception as exc:  # noqa: BLE001
        logger.debug("OPEN SCHEMA %s deferred (schema may not exist yet): %s", schema, exc)


@contextmanager
def get_db() -> Generator[pyexasol.ExaConnection, None, None]:
    """Yield an Exasol connection or raise ExasolUnavailableError."""
    conn: pyexasol.ExaConnection | None = None
    settings = get_settings()
    try:
        conn = _make_connection()
        _open_schema(conn)
        logger.debug("Exasol connection opened")
        yield conn
    except _connection_error_types() as exc:
        logger.error("Exasol connection failed at %s: %s", settings.exasol_dsn, type(exc).__name__)
        raise ExasolUnavailableError(
            f"Cannot reach Exasol at {settings.exasol_dsn}. "
            "Start Exasol Personal (see README) and confirm EXASOL_HOST/PORT/USER in .env."
        ) from exc
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


def probe_connection() -> DatabaseStatus:
    """Return current database reachability without raising."""
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        return DatabaseStatus.CONNECTED
    except ExasolUnavailableError:
        return DatabaseStatus.DEGRADED
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error probing Exasol: %s", type(exc).__name__)
        return DatabaseStatus.DEGRADED
