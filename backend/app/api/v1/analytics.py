"""
Analytics endpoints: materials, market signals, scenarios, exposures,
concentration, recommendations, evidence traces.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.connection import ExasolUnavailableError, get_db
from app.schemas.common import (
    APIResponse,
    ConcentrationSchema,
    DecisionCreateSchema,
    ExposureResultSchema,
    MarketSignalSchema,
    MaterialSchema,
    RecommendationSchema,
    ScenarioCreateSchema,
    ScenarioSchema,
    SupplierQuoteSchema,
    SupplierSchema,
)
from app.services import analytics as svc
from app.services.evidence import build_evidence_trace

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


def _db_error(exc: ExasolUnavailableError) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


# ── Materials ─────────────────────────────────────────────────────────────────

@router.get("/materials", response_model=List[MaterialSchema])
def list_materials() -> list[MaterialSchema]:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT material_id, material_code, material_name, "
                "category, sub_category, unit_of_measure, normalised_name "
                "FROM MATERIALS ORDER BY material_name"
            ).fetchall()
        return [
            MaterialSchema(
                material_id=r[0], material_code=r[1], material_name=r[2],
                category=r[3], sub_category=r[4], unit_of_measure=r[5] or "kg",
                normalised_name=r[6],
            )
            for r in rows
        ]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Suppliers ─────────────────────────────────────────────────────────────────

@router.get("/suppliers", response_model=List[SupplierSchema])
def list_suppliers() -> list[SupplierSchema]:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT supplier_id, supplier_name, city, supplier_state, "
                "supplier_tier, lead_time_days, quality_score "
                "FROM SUPPLIERS ORDER BY supplier_name"
            ).fetchall()
        return [
            SupplierSchema(
                supplier_id=r[0], supplier_name=r[1], city=r[2], state=r[3],
                supplier_tier=r[4], lead_time_days=r[5],
                quality_score=Decimal(str(r[6])) if r[6] else None,
            )
            for r in rows
        ]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Market signals ────────────────────────────────────────────────────────────

@router.get("/market-signals", response_model=List[MarketSignalSchema])
def list_market_signals(
    commodity_code: str | None = Query(default=None),
    limit: int = Query(default=180, ge=1, le=2000),
) -> list[MarketSignalSchema]:
    try:
        with get_db() as conn:
            if commodity_code:
                rows = conn.execute(
                    "SELECT signal_id, commodity_code, signal_date, price, "
                    f"currency, unit, signal_source FROM MARKET_SIGNALS "
                    f"WHERE commodity_code = {{cc}} ORDER BY signal_date DESC LIMIT {limit}",
                    {"cc": commodity_code},
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT signal_id, commodity_code, signal_date, price, "
                    "currency, unit, signal_source FROM V_LATEST_MARKET_SIGNAL "
                    "ORDER BY commodity_code"
                ).fetchall()
        return [
            MarketSignalSchema(
                signal_id=r[0], commodity_code=r[1], signal_date=r[2],
                price=Decimal(str(r[3])), currency=r[4], unit=r[5], source=r[6],
            )
            for r in rows
        ]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Concentration ─────────────────────────────────────────────────────────────

@router.get("/concentration", response_model=List[ConcentrationSchema])
def material_concentration() -> list[ConcentrationSchema]:
    try:
        with get_db() as conn:
            return svc.get_material_concentration(conn)
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Scenarios ─────────────────────────────────────────────────────────────────

@router.post("/scenarios", response_model=ScenarioSchema, status_code=201)
def create_scenario(body: ScenarioCreateSchema) -> ScenarioSchema:
    try:
        with get_db() as conn:
            sid = svc.create_scenario(
                conn,
                name=body.scenario_name,
                commodity_code=body.commodity_code,
                shock_pct=body.shock_pct,
                shock_direction=body.shock_direction,
                period_start=body.analysis_period_start,
                period_end=body.analysis_period_end,
            )
            scenario = svc.get_scenario(conn, sid)
        return scenario  # type: ignore[return-value]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


@router.get("/scenarios", response_model=List[ScenarioSchema])
def list_scenarios() -> list[ScenarioSchema]:
    try:
        with get_db() as conn:
            return svc.list_scenarios(conn)
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioSchema)
def get_scenario(scenario_id: str) -> ScenarioSchema:
    try:
        with get_db() as conn:
            sc = svc.get_scenario(conn, scenario_id)
        if not sc:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return sc
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Exposure Calculation ──────────────────────────────────────────────────────

@router.post("/scenarios/{scenario_id}/calculate", response_model=List[ExposureResultSchema])
def calculate_scenario(scenario_id: str) -> list[ExposureResultSchema]:
    """
    Execute the scenario_impact SQL query in Exasol and persist results.
    Formulas are documented in database/queries/scenario_impact.sql.
    """
    try:
        with get_db() as conn:
            return svc.calculate_exposure(conn, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


@router.get("/scenarios/{scenario_id}/results", response_model=List[ExposureResultSchema])
def get_exposure_results(scenario_id: str) -> list[ExposureResultSchema]:
    try:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT er.material_id, m.material_name, er.commodity_code,
                          mcm.commodity_name, er.exposure_weight, mcm.confidence,
                          er.observed_spend_inr, er.exposed_spend_inr, er.incremental_cost_inr
                   FROM EXPOSURE_RESULTS er
                   JOIN MATERIALS m ON m.material_id = er.material_id
                   JOIN MATERIAL_COMMODITY_MAP mcm
                     ON mcm.material_id = er.material_id
                    AND mcm.commodity_code = er.commodity_code
                   WHERE er.scenario_id = {sid}
                   ORDER BY er.incremental_cost_inr DESC""",
                {"sid": scenario_id},
            ).fetchall()
        return [
            ExposureResultSchema(
                material_id=r[0], material_name=r[1], commodity_code=r[2],
                commodity_name=r[3] or r[2], exposure_weight=Decimal(str(r[4])),
                mapping_confidence=r[5] or "UNKNOWN",
                observed_spend_inr=Decimal(str(r[6])),
                exposed_spend_inr=Decimal(str(r[7])),
                incremental_cost_inr=Decimal(str(r[8])),
            )
            for r in rows
        ]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Supplier Comparison ───────────────────────────────────────────────────────

@router.get("/supplier-comparison/{material_id}", response_model=List[SupplierQuoteSchema])
def supplier_comparison(
    material_id: str,
    required_qty: float = Query(default=1000.0, gt=0),
    max_lead_time: float = Query(default=30.0, gt=0),
    min_quality: float = Query(default=6.0, ge=0, le=10),
) -> list[SupplierQuoteSchema]:
    try:
        with get_db() as conn:
            return svc.get_supplier_alternatives(
                conn, material_id, required_qty, max_lead_time, min_quality
            )
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Recommendations ───────────────────────────────────────────────────────────

@router.post("/recommendations", response_model=RecommendationSchema, status_code=201)
def generate_recommendation(
    scenario_id: str,
    material_id: str,
    required_qty: float = Query(default=1000.0, gt=0),
    max_lead_time: float = Query(default=30.0, gt=0),
    min_quality: float = Query(default=6.0, ge=0, le=10),
) -> RecommendationSchema:
    """Generate and persist a recommendation for a material in a scenario."""
    try:
        with get_db() as conn:
            # Calculate exposure first
            exposures = svc.calculate_exposure(conn, scenario_id)
            exposure = next((e for e in exposures if e.material_id == material_id), None)
            if not exposure:
                raise HTTPException(
                    status_code=404,
                    detail=f"No exposure result for material {material_id} in scenario {scenario_id}",
                )
            alternatives = svc.get_supplier_alternatives(
                conn, material_id, required_qty, max_lead_time, min_quality
            )
            return svc.generate_recommendation(
                conn, scenario_id, material_id, exposure, alternatives, required_qty
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


@router.get("/recommendations", response_model=List[RecommendationSchema])
def list_recommendations(scenario_id: str | None = None) -> list[RecommendationSchema]:
    try:
        with get_db() as conn:
            if scenario_id:
                rows = conn.execute(
                    "SELECT recommendation_id, scenario_id, material_id, action_code, "
                    "action_summary, confidence, requires_human_review, "
                    "alternative_supplier_id, estimated_saving_inr, "
                    "saving_basis, evidence_summary "
                    "FROM RECOMMENDATIONS WHERE scenario_id = {sid} "
                    "ORDER BY created_at DESC",
                    {"sid": scenario_id},
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT recommendation_id, scenario_id, material_id, action_code, "
                    "action_summary, confidence, requires_human_review, "
                    "alternative_supplier_id, estimated_saving_inr, "
                    "saving_basis, evidence_summary "
                    "FROM RECOMMENDATIONS ORDER BY created_at DESC LIMIT 50"
                ).fetchall()
        return [
            RecommendationSchema(
                recommendation_id=r[0], scenario_id=r[1], material_id=r[2],
                action_code=r[3], action_summary=r[4], confidence=r[5],
                requires_human_review=bool(r[6]), alternative_supplier_id=r[7],
                estimated_saving_inr=Decimal(str(r[8])) if r[8] else None,
                saving_basis=r[9], evidence_summary=r[10],
            )
            for r in rows
        ]
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Evidence Trace ────────────────────────────────────────────────────────────

@router.get("/evidence/{recommendation_id}")
def get_evidence_trace(recommendation_id: str) -> dict:
    """Return the complete evidence chain for a recommendation."""
    try:
        with get_db() as conn:
            trace = build_evidence_trace(conn, recommendation_id)
        if "error" in trace:
            raise HTTPException(status_code=404, detail=trace["error"])
        return trace
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Decisions ─────────────────────────────────────────────────────────────────

@router.post("/decisions", status_code=201)
def record_decision(body: DecisionCreateSchema) -> dict:
    """Record a human approval, rejection or deferral of a recommendation."""
    import uuid
    try:
        with get_db() as conn:
            decision_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO DECISION_EVENTS
                   (decision_id, recommendation_id, decision, decided_by, decision_notes)
                   VALUES ({did}, {rid}, {decision}, {by}, {notes})""",
                {
                    "did": decision_id,
                    "rid": body.recommendation_id,
                    "decision": body.decision,
                    "by": body.decided_by,
                    "notes": body.decision_notes,
                },
            )
        return {"decision_id": decision_id, "status": "recorded"}
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Overview Dashboard ────────────────────────────────────────────────────────

@router.get("/overview")
def overview_dashboard() -> dict:
    """Aggregate stats for the overview dashboard."""
    try:
        with get_db() as conn:
            total_spend_row = conn.execute(
                "SELECT SUM(total_value_inr) FROM PURCHASE_LINES WHERE is_duplicate = FALSE"
            ).fetchone()
            exposed_row = conn.execute(
                "SELECT COUNT(DISTINCT material_id) FROM MATERIAL_COMMODITY_MAP"
            ).fetchone()
            high_conc_row = conn.execute(
                "SELECT COUNT(*) FROM V_MATERIAL_HHI WHERE concentration_level = 'HIGH'"
            ).fetchone()
            supplier_count_row = conn.execute("SELECT COUNT(*) FROM SUPPLIERS").fetchone()
            recent_scenario_row = conn.execute(
                "SELECT scenario_name, created_at FROM SCENARIO_RUNS "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        return {
            "total_purchase_spend_inr": float(total_spend_row[0]) if total_spend_row[0] else 0,
            "exposed_material_count": int(exposed_row[0]) if exposed_row[0] else 0,
            "high_concentration_materials": int(high_conc_row[0]) if high_conc_row[0] else 0,
            "supplier_count": int(supplier_count_row[0]) if supplier_count_row[0] else 0,
            "latest_scenario": recent_scenario_row[0] if recent_scenario_row else None,
        }
    except ExasolUnavailableError as exc:
        raise _db_error(exc)


# ── Spend History ─────────────────────────────────────────────────────────────

@router.get("/spend-history")
def spend_history(material_id: str | None = None) -> dict:
    """Monthly spend history, optionally filtered by material."""
    try:
        with get_db() as conn:
            if material_id:
                rows = conn.execute(
                    "SELECT spend_month, total_spend_inr, total_quantity, "
                    "distinct_supplier_count FROM V_MATERIAL_SPEND "
                    "WHERE material_id = {mid} ORDER BY spend_month",
                    {"mid": material_id},
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT spend_month, SUM(total_spend_inr) AS total_spend_inr "
                    "FROM V_MATERIAL_SPEND GROUP BY spend_month ORDER BY spend_month"
                ).fetchall()
        return {
            "material_id": material_id,
            "history": [
                {"month": str(r[0]), "spend_inr": float(r[1])}
                for r in rows
            ],
        }
    except ExasolUnavailableError as exc:
        raise _db_error(exc)
