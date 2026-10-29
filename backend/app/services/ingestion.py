"""
Data ingestion service for purchase CSV/Excel uploads.
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
import pyexasol  # type: ignore

from app.db.connection import import_dataframe

logger = logging.getLogger(__name__)

REQUIRED_PURCHASE_COLUMNS = {
    "po_number", "purchase_date", "material_code",
    "supplier_name", "quantity", "unit_price_inr",
}


def _normalise_text(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", " ", str(s).strip().upper())


def _row_fingerprint(row: pd.Series) -> str:
    key = "|".join([
        str(row.get("po_number", "")),
        str(row.get("purchase_date", "")),
        str(row.get("material_code", "")),
        str(row.get("supplier_name", "")),
        str(row.get("quantity", "")),
    ])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _stored_fingerprint(po_number: Any, purchase_date: Any, material_id: Any, quantity: Any) -> str:
    key = "|".join([str(po_number), str(purchase_date), str(material_id), str(quantity)])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _resolve_material_id(conn: pyexasol.ExaConnection, material_code: str) -> str | None:
    row = conn.execute(
        "SELECT material_id FROM MATERIALS WHERE UPPER(material_code) = {code}",
        {"code": material_code.upper()},
    ).fetchone()
    return row[0] if row else None


def _resolve_supplier_id(conn: pyexasol.ExaConnection, supplier_name: str) -> str | None:
    row = conn.execute(
        "SELECT supplier_id FROM SUPPLIERS WHERE UPPER(supplier_name) = {name}",
        {"name": supplier_name.upper()},
    ).fetchone()
    return row[0] if row else None


def _get_existing_fingerprints(conn: pyexasol.ExaConnection) -> set[str]:
    rows = conn.execute(
        "SELECT po_number, purchase_date, material_id, quantity FROM PURCHASE_LINES"
    ).fetchall()
    return {_stored_fingerprint(r[0], r[1], r[2], r[3]) for r in rows}


def _insert_ingestion(
    conn: pyexasol.ExaConnection,
    ingestion_id: str,
    filename: str,
    source_type: str,
    row_count: int,
    status: str,
    started_at: str,
    error: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO INGESTION_RECORDS
           (ingestion_id, file_name, source_type, row_count, ingest_status, started_at, error_details)
           VALUES ({iid}, {fname}, {stype}, {rc}, {status}, {started}, {error})""",
        {
            "iid": ingestion_id,
            "fname": filename,
            "stype": source_type,
            "rc": row_count,
            "status": status,
            "started": started_at,
            "error": error,
        },
    )


def _complete_ingestion(
    conn: pyexasol.ExaConnection,
    ingestion_id: str,
    accepted: int,
    rejected: int,
    duplicates: int,
    status: str,
    errors: str | None,
) -> None:
    conn.execute(
        """UPDATE INGESTION_RECORDS SET
           accepted_count = {acc}, rejected_count = {rej},
           duplicate_count = {dup}, ingest_status = {status},
           completed_at = CURRENT_TIMESTAMP,
           error_details = {errors}
           WHERE ingestion_id = {iid}""",
        {
            "acc": accepted,
            "rej": rejected,
            "dup": duplicates,
            "status": status,
            "errors": errors,
            "iid": ingestion_id,
        },
    )


def ingest_purchase_csv(
    conn: pyexasol.ExaConnection,
    file_bytes: bytes,
    filename: str,
    source_type: str = "CSV_UPLOAD",
) -> dict[str, Any]:
    ingestion_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(file_bytes))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(file_bytes))
        else:
            _insert_ingestion(conn, ingestion_id, filename, source_type, 0, "FAILED", started_at, "Unsupported format")
            return {
                "ingestion_id": ingestion_id,
                "status": "FAILED",
                "error": "Unsupported format",
                "total_rows": 0, "accepted": 0, "rejected": 0, "duplicates": 0,
            }
    except Exception as exc:
        _insert_ingestion(
            conn, ingestion_id, filename, source_type, 0, "FAILED", started_at, f"Could not parse file: {exc}"
        )
        return {
            "ingestion_id": ingestion_id,
            "status": "FAILED",
            "error": f"Could not parse file: {exc}",
            "total_rows": 0, "accepted": 0, "rejected": 0, "duplicates": 0,
        }

    df.columns = df.columns.str.lower().str.strip()
    missing_cols = REQUIRED_PURCHASE_COLUMNS - set(df.columns)
    if missing_cols:
        _insert_ingestion(
            conn, ingestion_id, filename, source_type, len(df), "FAILED", started_at,
            f"Missing required columns: {sorted(missing_cols)}",
        )
        return {
            "ingestion_id": ingestion_id,
            "status": "FAILED",
            "error": f"Missing required columns: {sorted(missing_cols)}",
            "total_rows": len(df), "accepted": 0, "rejected": 0, "duplicates": 0,
        }

    if df.empty:
        _insert_ingestion(conn, ingestion_id, filename, source_type, 0, "FAILED", started_at, "File contains no data rows")
        return {
            "ingestion_id": ingestion_id,
            "status": "FAILED",
            "error": "File contains no data rows",
            "total_rows": 0, "accepted": 0, "rejected": 0, "duplicates": 0,
        }

    total_rows = len(df)
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    duplicate_count = 0
    existing_fps = _get_existing_fingerprints(conn)

    _insert_ingestion(conn, ingestion_id, filename, source_type, total_rows, "PROCESSING", started_at)

    try:
        for idx, row in df.iterrows():
            row_errors: list[str] = []
            material_code = _normalise_text(row.get("material_code", ""))
            supplier_name = _normalise_text(row.get("supplier_name", ""))

            material_id = _resolve_material_id(conn, material_code) if material_code else None
            if not material_id:
                row_errors.append(f"Unknown material_code '{row.get('material_code')}'")

            supplier_id = _resolve_supplier_id(conn, supplier_name) if supplier_name else None
            if not supplier_id:
                row_errors.append(f"Unknown supplier_name '{row.get('supplier_name')}'")

            try:
                quantity = float(row.get("quantity", 0))
                if quantity <= 0:
                    row_errors.append("quantity must be > 0")
            except (ValueError, TypeError):
                row_errors.append("quantity is not numeric")
                quantity = 0.0

            try:
                unit_price = float(row.get("unit_price_inr", 0))
                if unit_price < 0:
                    row_errors.append("unit_price_inr must be >= 0")
            except (ValueError, TypeError):
                row_errors.append("unit_price_inr is not numeric")
                unit_price = 0.0

            try:
                purchase_date = pd.to_datetime(row.get("purchase_date")).date()
            except Exception:
                row_errors.append(f"Cannot parse purchase_date '{row.get('purchase_date')}'")
                purchase_date = None

            if row_errors:
                rejected_rows.append({"row": int(idx) + 2, "errors": row_errors})
                continue

            fp = _stored_fingerprint(row.get("po_number", ""), purchase_date, material_id, quantity)
            is_duplicate = fp in existing_fps
            if is_duplicate:
                duplicate_count += 1
                existing_fps.add(fp)
                continue

            existing_fps.add(fp)
            po_number = str(row.get("po_number", f"UP-{idx}"))
            accepted_rows.append({
                "line_id": str(uuid.uuid4()),
                "po_number": po_number,
                "purchase_date": str(purchase_date),
                "material_id": material_id,
                "supplier_id": supplier_id,
                "quantity": quantity,
                "unit_price_inr": unit_price,
                "total_value_inr": round(quantity * unit_price, 4),
                "currency": "INR",
                "inr_exchange_rate": 1.0,
                "ingestion_id": ingestion_id,
                "purchase_source": source_type,
                "is_duplicate": False,
            })

        if accepted_rows:
            import_dataframe(conn, pd.DataFrame(accepted_rows), "PURCHASE_LINES")

        status = "COMPLETED_WITH_ERRORS" if rejected_rows or duplicate_count else "COMPLETED"
        _complete_ingestion(
            conn, ingestion_id, len(accepted_rows), len(rejected_rows), duplicate_count,
            status, str(rejected_rows[:20]) if rejected_rows else None,
        )
    except Exception as exc:
        _complete_ingestion(conn, ingestion_id, 0, total_rows, 0, "FAILED", str(exc))
        raise

    return {
        "ingestion_id": ingestion_id,
        "status": status,
        "total_rows": total_rows,
        "accepted": len(accepted_rows),
        "rejected": len(rejected_rows),
        "duplicates": duplicate_count,
        "rejected_details": rejected_rows[:50],
    }
