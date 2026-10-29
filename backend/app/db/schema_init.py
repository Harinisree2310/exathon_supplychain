"""
Exasol schema initialisation.

Sequence:
  1. CREATE SCHEMA IF NOT EXISTS / OPEN SCHEMA
  2. Create tables from database/schema/*.sql
  3. Create views from database/views/*.sql
  4. Verify required tables, views, and columns

Idempotent: CREATE TABLE IF NOT EXISTS and CREATE OR REPLACE VIEW.
Does not DROP existing user data. If an existing table is missing required
columns, raises SchemaIncompatibleError so the operator can choose a new
schema or repair manually.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pyexasol  # type: ignore

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = PROJECT_ROOT / "database" / "schema"
VIEWS_DIR = PROJECT_ROOT / "database" / "views"

REQUIRED_TABLES = [
    "SUPPLIERS",
    "MATERIALS",
    "PURCHASE_LINES",
    "MATERIAL_COMMODITY_MAP",
    "MARKET_SIGNALS",
    "SUPPLIER_QUOTATIONS",
    "SCENARIO_RUNS",
    "EXPOSURE_RESULTS",
    "SUPPLIER_CONCENTRATION",
    "RECOMMENDATIONS",
    "DECISION_EVENTS",
    "INGESTION_RECORDS",
]

REQUIRED_VIEWS = [
    "V_MATERIAL_SPEND",
    "V_SUPPLIER_SHARE",
    "V_MATERIAL_HHI",
    "V_MATERIAL_EXPOSURE",
    "V_LATEST_MARKET_SIGNAL",
    "V_SUPPLIER_QUOTE_COMPARISON",
]

# Canonical columns that previously drifted between CSV, SQL, and DDL.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "SUPPLIERS": {"SUPPLIER_ID", "SUPPLIER_NAME", "SUPPLIER_STATE"},
    "MARKET_SIGNALS": {"SIGNAL_ID", "COMMODITY_CODE", "SIGNAL_SOURCE"},
    "PURCHASE_LINES": {"LINE_ID", "PURCHASE_SOURCE", "IS_DUPLICATE"},
    "INGESTION_RECORDS": {"INGESTION_ID", "INGEST_STATUS"},
}


class SchemaIncompatibleError(RuntimeError):
    """Existing schema is missing required columns; refusing to auto-drop data."""


def _quote_ident(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch == "_")
    if not cleaned or cleaned.upper() != name.upper():
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return cleaned.upper()


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL on semicolons outside strings, quotes, and comments."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":
                buf.append(nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            buf.append(ch)
            if ch == '"':
                in_double = False
            i += 1
            continue

        if ch == "-" and nxt == "-":
            buf.append(ch)
            buf.append(nxt)
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            buf.append(ch)
            buf.append(nxt)
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    remainder = "".join(buf).strip().rstrip(";")
    if remainder:
        statements.append(remainder)
    return [s for s in statements if s and not _is_comment_only(s)]


def _is_comment_only(stmt: str) -> bool:
    stripped = []
    for line in stmt.splitlines():
        t = line.strip()
        if t and not t.startswith("--"):
            stripped.append(t)
    text = " ".join(stripped)
    return not text or text.startswith("/*")


def _execute_sql_file(conn: pyexasol.ExaConnection, path: Path) -> int:
    sql = path.read_text(encoding="utf-8")
    count = 0
    for statement in split_sql_statements(sql):
        conn.execute(statement)
        count += 1
    return count


def _existing_names(conn: pyexasol.ExaConnection, schema: str, object_type: str) -> set[str]:
    if object_type.upper() == "VIEW":
        sql = "SELECT view_name FROM EXA_ALL_VIEWS WHERE view_schema = {schema}"
    else:
        sql = "SELECT table_name FROM EXA_ALL_TABLES WHERE table_schema = {schema}"
    rows = conn.execute(sql, {"schema": schema.upper()}).fetchall()
    return {str(r[0]).upper() for r in rows}


def _existing_columns(conn: pyexasol.ExaConnection, schema: str, table: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name
        FROM EXA_ALL_COLUMNS
        WHERE column_schema = {schema}
          AND column_table = {table}
        """,
        {"schema": schema.upper(), "table": table.upper()},
    ).fetchall()
    return {str(r[0]).upper() for r in rows}


def verify_schema(conn: pyexasol.ExaConnection, schema: str) -> dict[str, list[str]]:
    """Confirm required tables/views/columns exist. Raises on incompatible DDL."""
    tables = _existing_names(conn, schema, "TABLE")
    views = _existing_names(conn, schema, "VIEW")
    missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
    missing_views = [v for v in REQUIRED_VIEWS if v not in views]
    missing_columns: list[str] = []

    for table, cols in REQUIRED_COLUMNS.items():
        if table not in tables:
            continue
        present = _existing_columns(conn, schema, table)
        for col in cols:
            if col not in present:
                missing_columns.append(f"{table}.{col}")

    if missing_columns:
        raise SchemaIncompatibleError(
            "Existing schema is missing required columns: "
            + ", ".join(missing_columns)
            + ". SupplyLens will not drop your data automatically. "
            "Use a new EXASOL_SCHEMA value, or empty/repair the schema, then retry."
        )

    return {
        "missing_tables": missing_tables,
        "missing_views": missing_views,
        "tables": sorted(tables),
        "views": sorted(views),
    }


def init_schema(conn: pyexasol.ExaConnection, schema: str) -> dict[str, object]:
    """Create schema, tables, and analytical views. Idempotent."""
    ident = _quote_ident(schema)
    logger.info("Initialising schema %s", ident)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {ident}")
    conn.execute(f"OPEN SCHEMA {ident}")

    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    view_files = sorted(VIEWS_DIR.glob("*.sql"))
    if not sql_files:
        logger.warning("No SQL files found in %s", SCHEMA_DIR)

    table_statements = 0
    for sql_file in sql_files:
        logger.info("Executing schema file: %s", sql_file.name)
        table_statements += _execute_sql_file(conn, sql_file)

    view_statements = 0
    for view_file in view_files:
        logger.info("Executing view file: %s", view_file.name)
        view_statements += _execute_sql_file(conn, view_file)

    verification = verify_schema(conn, ident)
    if verification["missing_tables"] or verification["missing_views"]:
        raise RuntimeError(
            "Schema verification failed. Missing tables: "
            f"{verification['missing_tables']}; missing views: {verification['missing_views']}"
        )

    logger.info("Schema initialisation complete")
    return {
        "schema": ident,
        "table_statements": table_statements,
        "view_statements": view_statements,
        "tables": REQUIRED_TABLES,
        "views": REQUIRED_VIEWS,
    }
