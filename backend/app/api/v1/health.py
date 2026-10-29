"""Health check endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.connection import DatabaseStatus, get_db, probe_connection
from app.schemas.common import HealthStatus

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthStatus)
def health_check() -> HealthStatus:
    """
    Returns API status and live Exasol connectivity.
    Never silently reports 'ok' when the database is unreachable.
    """
    db_status = probe_connection()
    return HealthStatus(
        api="ok",
        database=db_status.value,
        database_dsn=settings.exasol_dsn,
        version="1.0.0",
        environment=settings.environment,
    )


@router.get("/health/db")
def db_health() -> JSONResponse:
    """Detailed Exasol health check with table row counts."""
    from app.services.analytics import get_db_row_counts
    status = probe_connection()
    counts: dict = {}
    if status == DatabaseStatus.CONNECTED:
        with get_db() as conn:
            counts = get_db_row_counts(conn)
    return JSONResponse({
        "database": status.value,
        "dsn": settings.exasol_dsn,
        "table_counts": counts,
    })
