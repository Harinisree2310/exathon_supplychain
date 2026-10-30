"""Shared Pydantic schemas used across multiple endpoints."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class APIResponse(BaseModel):
    """Generic envelope for all API responses."""
    success: bool = True
    message: str = "OK"
    data: Any = None


class HealthStatus(BaseModel):
    api: str = "ok"
    database: str  # "connected" | "degraded"
    database_dsn: str
    version: str = "1.0.0"
    environment: str


class MaterialSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    material_code: str
    material_name: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    unit_of_measure: str = "kg"
    normalised_name: Optional[str] = None


class SupplierSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    supplier_id: str
    supplier_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    supplier_tier: Optional[str] = None
    lead_time_days: Optional[int] = None
    quality_score: Optional[Decimal] = None

    @field_serializer("quality_score", when_used="json")
    def serialize_quality_score(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None


class MarketSignalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    signal_id: str
    commodity_code: str
    signal_date: date
    price: Decimal
    currency: str
    unit: Optional[str] = None
    source: str

    @field_serializer("price", when_used="json")
    def serialize_price(self, value: Decimal) -> float:
        return float(value)


class ExposureResultSchema(BaseModel):
    material_id: str
    material_name: str
    commodity_code: str
    commodity_name: str
    exposure_weight: Decimal
    mapping_confidence: str
    observed_spend_inr: Decimal
    exposed_spend_inr: Decimal
    incremental_cost_inr: Decimal
    line_count: Optional[int] = None
    distinct_supplier_count: Optional[int] = None

    @field_serializer(
        "exposure_weight", "observed_spend_inr", "exposed_spend_inr",
        "incremental_cost_inr", when_used="json",
    )
    def serialize_numeric_values(self, value: Decimal) -> float:
        return float(value)


class SupplierQuoteSchema(BaseModel):
    quote_id: str
    supplier_id: str
    supplier_name: str
    material_id: str
    material_name: str
    unit_price_inr: Optional[Decimal] = None
    min_order_qty: Optional[Decimal] = None
    max_capacity_qty: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    quality_score: Optional[Decimal] = None
    valid_until: Optional[date] = None
    feasibility_status: str
    price_rank: int
    notes: Optional[str] = None

    @field_serializer(
        "unit_price_inr", "min_order_qty", "max_capacity_qty", "quality_score",
        when_used="json",
    )
    def serialize_numeric_values(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None


class ScenarioCreateSchema(BaseModel):
    scenario_name: str = Field(..., min_length=3, max_length=200)
    commodity_code: str = Field(..., min_length=3, max_length=50)
    shock_pct: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    shock_direction: str = Field(default="UP", pattern="^(UP|DOWN)$")
    analysis_period_start: date
    analysis_period_end: date


class ScenarioSchema(BaseModel):
    scenario_id: str
    scenario_name: str
    commodity_code: str
    shock_pct: Decimal
    shock_direction: str
    analysis_period_start: Optional[date] = None
    analysis_period_end: Optional[date] = None
    created_at: Optional[datetime] = None

    @field_serializer("shock_pct", when_used="json")
    def serialize_shock_pct(self, value: Decimal) -> float:
        return float(value)


class RecommendationSchema(BaseModel):
    recommendation_id: str
    scenario_id: str
    material_id: str
    action_code: str
    action_summary: str
    confidence: str
    requires_human_review: bool
    alternative_supplier_id: Optional[str] = None
    estimated_saving_inr: Optional[Decimal] = None
    saving_basis: Optional[str] = None
    evidence_summary: Optional[str] = None

    @field_serializer("estimated_saving_inr", when_used="json")
    def serialize_estimated_saving(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None


class DecisionCreateSchema(BaseModel):
    recommendation_id: str
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|DEFERRED)$")
    decided_by: str = Field(..., min_length=1, max_length=100)
    decision_notes: Optional[str] = Field(default=None, max_length=2000)


class ConcentrationSchema(BaseModel):
    material_id: str
    material_name: str
    hhi: Decimal
    concentration_level: str
    supplier_count: int
    dominant_share_pct: Decimal

    @field_serializer("hhi", "dominant_share_pct", when_used="json")
    def serialize_numeric_values(self, value: Decimal) -> float:
        return float(value)


class DataQualitySummarySchema(BaseModel):
    total_materials: int
    total_suppliers: int
    total_purchase_lines: int
    total_market_signals: int
    materials_with_mapping: int
    materials_without_mapping: int
    stale_signal_count: int  # commodities whose latest signal is over 30 days old
    incomplete_quotations: int
    data_source: str = "SYNTHETIC"
    is_synthetic: bool = True
