"""
Load synthetic CSVs into Exasol using pyexasol's fast HTTP import.

Usage:
    python -m app.db.seed_loader
    python -m app.db.seed_loader --reset

CSV headers that differ from canonical DDL are remapped here:
  suppliers.state            -> SUPPLIERS.supplier_state
  market_signals.source      -> MARKET_SIGNALS.signal_source
  purchase_lines.source      -> PURCHASE_LINES.purchase_source
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pyexasol  # type: ignore

from app.db.connection import import_dataframe
from app.db.schema_init import REQUIRED_TABLES, REQUIRED_VIEWS, init_schema

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"

TABLE_CSV_MAP: list[tuple[str, str]] = [
    ("SUPPLIERS", "suppliers.csv"),
    ("MATERIALS", "materials.csv"),
    ("MATERIAL_COMMODITY_MAP", "commodity_map.csv"),
    ("MARKET_SIGNALS", "market_signals.csv"),
    ("PURCHASE_LINES", "purchase_lines.csv"),
    ("SUPPLIER_QUOTATIONS", "supplier_quotations.csv"),
    ("SCENARIO_RUNS", "scenario_runs.csv"),
]

# Truncate children before parents when force-reloading.
TRUNCATE_ORDER = [
    "DECISION_EVENTS",
    "RECOMMENDATIONS",
    "EXPOSURE_RESULTS",
    "SUPPLIER_CONCENTRATION",
    "PURCHASE_LINES",
    "SUPPLIER_QUOTATIONS",
    "MATERIAL_COMMODITY_MAP",
    "MARKET_SIGNALS",
    "SCENARIO_RUNS",
    "INGESTION_RECORDS",
    "MATERIALS",
    "SUPPLIERS",
]

CSV_COLUMN_MAP: dict[str, dict[str, str]] = {
    "SUPPLIERS": {"state": "supplier_state"},
    "MARKET_SIGNALS": {"source": "signal_source"},
    "PURCHASE_LINES": {"source": "purchase_source"},
}

TABLE_DEFAULTS: dict[str, dict[str, object]] = {
    "SUPPLIERS": {
        "supplier_country": "India",
        "is_synthetic": True,
    },
    "MATERIALS": {
        "is_synthetic": True,
    },
    "MARKET_SIGNALS": {
        "is_synthetic": True,
    },
    "SUPPLIER_QUOTATIONS": {
        "is_synthetic": True,
    },
}


def _prepare_dataframe(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared.columns = [str(c).strip() for c in prepared.columns]
    rename = CSV_COLUMN_MAP.get(table_name, {})
    prepared = prepared.rename(columns=rename)

    if table_name == "MATERIALS" and "normalised_name" not in prepared.columns:
        prepared["normalised_name"] = prepared["material_name"].astype(str).str.upper()

    for col, default in TABLE_DEFAULTS.get(table_name, {}).items():
        if col not in prepared.columns:
            prepared[col] = default

    prepared = prepared.where(pd.notnull(prepared), None)
    return prepared


def _table_count(conn: pyexasol.ExaConnection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def refresh_supplier_concentration(conn: pyexasol.ExaConnection) -> int:
    """Materialise V_SUPPLIER_SHARE into SUPPLIER_CONCENTRATION for audit snapshots."""
    conn.execute("TRUNCATE TABLE SUPPLIER_CONCENTRATION")
    conn.execute(
        """
        INSERT INTO SUPPLIER_CONCENTRATION (
            concentration_id, material_id, supplier_id,
            period_start, period_end,
            supplier_spend_inr, total_spend_inr, share_pct, hhi
        )
        SELECT
            'CONC-' || ss.material_id || '-' || ss.supplier_id,
            ss.material_id,
            ss.supplier_id,
            DATE '2025-07-01',
            DATE '2026-01-01',
            ss.supplier_spend_inr,
            ss.total_material_spend_inr,
            ss.share_pct,
            h.hhi
        FROM V_SUPPLIER_SHARE ss
        JOIN V_MATERIAL_HHI h ON h.material_id = ss.material_id
        """
    )
    return _table_count(conn, "SUPPLIER_CONCENTRATION")


def validate_seed(conn: pyexasol.ExaConnection) -> dict[str, int]:
    counts = {table: _table_count(conn, table) for table in REQUIRED_TABLES}
    orphans = conn.execute(
        """
        SELECT COUNT(*) FROM PURCHASE_LINES pl
        WHERE pl.material_id NOT IN (SELECT material_id FROM MATERIALS)
           OR pl.supplier_id NOT IN (SELECT supplier_id FROM SUPPLIERS)
        """
    ).fetchone()
    orphan_count = int(orphans[0]) if orphans else 0
    if orphan_count:
        raise RuntimeError(f"Referential check failed: {orphan_count} orphan purchase lines")
    counts["_orphan_purchase_lines"] = orphan_count
    return counts


def load_synthetic_data(conn: pyexasol.ExaConnection, force_reload: bool = False) -> dict[str, int]:
    """
    Load all synthetic CSV files into Exasol.

    Returns {table_name: rows_loaded}.
    Skips tables that already contain data unless force_reload=True.
    """
    results: dict[str, int] = {}

    if force_reload:
        logger.info("Force reload requested — truncating demo tables in FK order")
        for table_name in TRUNCATE_ORDER:
            try:
                conn.execute(f"TRUNCATE TABLE {table_name}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not truncate %s: %s", table_name, exc)

    for table_name, csv_filename in TABLE_CSV_MAP:
        csv_path = DATA_DIR / csv_filename
        if not csv_path.exists():
            logger.error("CSV not found: %s – run generate_dataset.py first", csv_path)
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        existing_count = _table_count(conn, table_name)
        if existing_count > 0 and not force_reload:
            logger.info("Skipping %s: already has %d rows", table_name, existing_count)
            results[table_name] = existing_count
            continue

        df = _prepare_dataframe(table_name, pd.read_csv(csv_path))
        import_dataframe(conn, df, table_name)
        final_count = _table_count(conn, table_name)
        results[table_name] = final_count
        logger.info("Loaded %s: %d rows", table_name, final_count)

    results["SUPPLIER_CONCENTRATION"] = refresh_supplier_concentration(conn)
    validation = validate_seed(conn)
    results.update({f"validated_{k}": v for k, v in validation.items() if not k.startswith("_")})
    results["orphan_purchase_lines"] = validation["_orphan_purchase_lines"]
    return results


def setup_database(conn: pyexasol.ExaConnection, schema: str, force_reload: bool = False) -> dict[str, object]:
    """Full repeatable setup: schema → views → seed → validate."""
    init = init_schema(conn, schema)
    load = load_synthetic_data(conn, force_reload=force_reload)
    return {
        "schema": init,
        "load": load,
        "tables": REQUIRED_TABLES,
        "views": REQUIRED_VIEWS,
    }


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.core.config import get_settings
    from app.core.logging_config import configure_logging
    from app.db.connection import get_db

    configure_logging()
    settings = get_settings()

    print(f"Connecting to Exasol at {settings.exasol_dsn} …")
    with get_db() as conn:
        summary = setup_database(conn, settings.exasol_schema, force_reload="--reset" in sys.argv)
        print("Setup complete:")
        for table, count in summary["load"].items():
            print(f"  {table}: {count}")
