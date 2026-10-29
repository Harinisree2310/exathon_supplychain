"""Data workspace endpoints: load demo, upload files, quality summary."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.db.connection import ExasolUnavailableError, get_db
from app.db.schema_init import init_schema
from app.db.seed_loader import load_synthetic_data
from app.schemas.common import APIResponse, DataQualitySummarySchema
from app.services.analytics import get_data_quality
from app.services.ingestion import ingest_purchase_csv

router = APIRouter(prefix="/data", tags=["data"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/load-demo", response_model=APIResponse)
def load_demo_data(force: bool = False) -> APIResponse:
    """
    Initialise Exasol schema and load the synthetic demo dataset.
    Safe to call multiple times (idempotent unless force=True).
    """
    try:
        with get_db() as conn:
            init_schema(conn, settings.exasol_schema)
            results = load_synthetic_data(conn, force_reload=force)
        return APIResponse(
            success=True,
            message="Demo dataset loaded",
            data={"tables": results},
        )
    except ExasolUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Exasol unavailable: {exc}",
        )


@router.get("/quality", response_model=DataQualitySummarySchema)
def data_quality() -> DataQualitySummarySchema:
    """Return data-quality statistics from Exasol."""
    try:
        with get_db() as conn:
            return get_data_quality(conn)
    except ExasolUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/upload/purchases", response_model=APIResponse)
async def upload_purchases(file: UploadFile = File(...)) -> APIResponse:
    """
    Upload a CSV or Excel file of purchase lines.
    Validates schema, normalises data and ingests into Exasol.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_ext = {".csv", ".xlsx", ".xls"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Use CSV or Excel.",
        )

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_bytes // 1024 // 1024} MB",
        )

    try:
        with get_db() as conn:
            result = ingest_purchase_csv(conn, content, file.filename)
        return APIResponse(
            success=result["status"] != "FAILED",
            message=result["status"],
            data=result,
        )
    except ExasolUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/template/purchases")
def download_purchase_template() -> Any:
    """Return a CSV template for purchase uploads."""
    from fastapi.responses import Response
    header = "po_number,purchase_date,material_code,supplier_name,quantity,unit_price_inr\n"
    sample = "PO-2026-00001,2026-01-05,HR-STEEL-COIL,AgroMet Industries,10,52000\n"
    return Response(content=header + sample, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=purchase_template.csv"})
