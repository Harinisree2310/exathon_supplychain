"""
SupplyLens FastAPI application entry point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import analytics, data, health, reports
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.connection import ExasolUnavailableError

settings = get_settings()
configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("SupplyLens starting – Exasol DSN: %s", settings.exasol_dsn)
    yield
    logger.info("SupplyLens shutting down")


app = FastAPI(
    title="SupplyLens API",
    description=(
        "Shock-to-Decision Intelligence for Indian SMBs. "
        "Powered by Exasol Personal analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(data.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(ExasolUnavailableError)
async def exasol_unavailable_handler(
    request: Request,
    exc: ExasolUnavailableError,
) -> JSONResponse:
    logger.error("Exasol unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "message": "Database unavailable",
            "detail": str(exc),
            "action": (
                "Ensure Exasol Personal is running via Podman. "
                "See README.md for setup instructions."
            ),
        },
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "SupplyLens",
        "tagline": "Shock-to-Decision Intelligence for Indian SMBs",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
