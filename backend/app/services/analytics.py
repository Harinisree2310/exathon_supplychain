"""
Analytical service layer.

All aggregations, HHI, exposure, and supplier comparison execute in Exasol.
Python orchestrates parameters, persists results, and applies recommendation rules.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyexasol  # type: ignore

from app.schemas.common import (
    ConcentrationSchema,
    DataQualitySummarySchema,
    ExposureResultSchema,
    RecommendationSchema,
    ScenarioSchema,
    SupplierQuoteSchema,
)

logger = logging.getLogger(__name__)

_QUERY_DIR = Path(__file__).resolve().parents[3] / "database" / "queries"


def _load_query(name: str) -> str:
    return (_QUERY_DIR / name).read_text(encoding="utf-8")


def get_db_row_counts(conn: pyexasol.ExaConnection) -> dict[str, int]:
    tables = [
        "SUPPLIERS", "MATERIALS", "PURCHASE_LINES",
        "MARKET_SIGNALS", "SCENARIO_RUNS", "RECOMMENDATIONS",
        "SUPPLIER_QUOTATIONS", "MATERIAL_COMMODITY_MAP",
        "EXPOSURE_RESULTS", "DECISION_EVENTS",
        "INGESTION_RECORDS", "SUPPLIER_CONCENTRATION",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = int(row[0]) if row and row[0] is not None else 0
    return counts


def get_data_quality(conn: pyexasol.ExaConnection) -> DataQualitySummarySchema:
    def scalar(sql: str) -> int:
        row = conn.execute(sql).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    total_mat = scalar("SELECT COUNT(*) FROM MATERIALS")
    total_sup = scalar("SELECT COUNT(*) FROM SUPPLIERS")
    total_pl = scalar("SELECT COUNT(*) FROM PURCHASE_LINES WHERE is_duplicate = FALSE")
    total_ms = scalar("SELECT COUNT(*) FROM MARKET_SIGNALS")
    mat_mapped = scalar("SELECT COUNT(DISTINCT material_id) FROM MATERIAL_COMMODITY_MAP")
    stale = scalar(
        """SELECT COUNT(*) FROM (
               SELECT commodity_code, MAX(signal_date) AS latest_signal_date
               FROM MARKET_SIGNALS
               GROUP BY commodity_code
           ) latest
           WHERE latest_signal_date < ADD_DAYS(CURRENT_DATE, -30)"""
    )
    incomplete_quotes = scalar(
        "SELECT COUNT(*) FROM SUPPLIER_QUOTATIONS WHERE unit_price_inr IS NULL OR max_capacity_qty IS NULL"
    )
    return DataQualitySummarySchema(
        total_materials=total_mat,
        total_suppliers=total_sup,
        total_purchase_lines=total_pl,
        total_market_signals=total_ms,
        materials_with_mapping=mat_mapped,
        materials_without_mapping=max(0, total_mat - mat_mapped),
        stale_signal_count=stale,
        incomplete_quotations=incomplete_quotes,
        data_source="SYNTHETIC",
        is_synthetic=True,
    )


def get_material_concentration(conn: pyexasol.ExaConnection) -> list[ConcentrationSchema]:
    rows = conn.execute(
        "SELECT material_id, material_name, hhi, concentration_level, "
        "supplier_count, dominant_share_pct FROM V_MATERIAL_HHI"
    ).fetchall()
    return [
        ConcentrationSchema(
            material_id=r[0],
            material_name=r[1],
            hhi=Decimal(str(r[2])),
            concentration_level=r[3],
            supplier_count=int(r[4]),
            dominant_share_pct=Decimal(str(r[5])),
        )
        for r in rows
    ]


def get_historical_quantity(conn: pyexasol.ExaConnection, material_id: str) -> float:
    row = conn.execute(
        """SELECT COALESCE(SUM(quantity), 0)
           FROM PURCHASE_LINES
           WHERE material_id = {mat_id} AND is_duplicate = FALSE""",
        {"mat_id": material_id},
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def create_scenario(
    conn: pyexasol.ExaConnection,
    name: str,
    commodity_code: str,
    shock_pct: Decimal,
    shock_direction: str,
    period_start: date,
    period_end: date,
    created_by: str = "user",
) -> str:
    if period_end < period_start:
        raise ValueError("analysis_period_end must be on or after analysis_period_start")
    scenario_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO SCENARIO_RUNS
           (scenario_id, scenario_name, commodity_code, shock_pct,
            shock_direction, analysis_period_start, analysis_period_end, created_by)
           VALUES ({scenario_id}, {scenario_name}, {commodity_code}, {shock_pct},
                   {shock_direction}, {period_start}, {period_end}, {created_by})""",
        {
            "scenario_id": scenario_id,
            "scenario_name": name,
            "commodity_code": commodity_code,
            "shock_pct": float(shock_pct),
            "shock_direction": shock_direction.upper(),
            "period_start": str(period_start),
            "period_end": str(period_end),
            "created_by": created_by,
        },
    )
    return scenario_id


def get_scenario(conn: pyexasol.ExaConnection, scenario_id: str) -> ScenarioSchema | None:
    row = conn.execute(
        "SELECT scenario_id, scenario_name, commodity_code, shock_pct, shock_direction, "
        "analysis_period_start, analysis_period_end, created_at FROM SCENARIO_RUNS "
        "WHERE scenario_id = {scenario_id}",
        {"scenario_id": scenario_id},
    ).fetchone()
    if not row:
        return None
    return ScenarioSchema(
        scenario_id=row[0],
        scenario_name=row[1],
        commodity_code=row[2],
        shock_pct=Decimal(str(row[3])),
        shock_direction=row[4],
        analysis_period_start=row[5],
        analysis_period_end=row[6],
        created_at=row[7],
    )


def list_scenarios(conn: pyexasol.ExaConnection) -> list[ScenarioSchema]:
    rows = conn.execute(
        "SELECT scenario_id, scenario_name, commodity_code, shock_pct, shock_direction, "
        "analysis_period_start, analysis_period_end, created_at "
        "FROM SCENARIO_RUNS ORDER BY created_at DESC"
    ).fetchall()
    return [
        ScenarioSchema(
            scenario_id=r[0], scenario_name=r[1], commodity_code=r[2],
            shock_pct=Decimal(str(r[3])), shock_direction=r[4],
            analysis_period_start=r[5], analysis_period_end=r[6], created_at=r[7],
        )
        for r in rows
    ]


def calculate_exposure(
    conn: pyexasol.ExaConnection,
    scenario_id: str,
) -> list[ExposureResultSchema]:
    scenario = get_scenario(conn, scenario_id)
    if not scenario:
        raise ValueError(f"Scenario not found: {scenario_id}")

    period_start = scenario.analysis_period_start or date(2025, 7, 1)
    period_end = scenario.analysis_period_end or date(2026, 1, 1)

    sql = _load_query("scenario_impact.sql")
    rows = conn.execute(
        sql,
        {
            "scenario_id": scenario_id,
            "period_start": str(period_start),
            "period_end": str(period_end),
        },
    ).fetchall()

    conn.execute(
        "DELETE FROM EXPOSURE_RESULTS WHERE scenario_id = {sid}",
        {"sid": scenario_id},
    )

    results: list[ExposureResultSchema] = []
    for r in rows:
        (
            _s_id, _s_name, commodity_code, _shock_pct, _shock_direction, _signed,
            material_id, material_name, exposure_weight, confidence,
            observed_spend, exposed_spend, incremental_cost,
            line_count, distinct_supplier_count,
        ) = r

        result_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO EXPOSURE_RESULTS
               (result_id, scenario_id, material_id, commodity_code,
                exposure_weight, observed_spend_inr, exposed_spend_inr, incremental_cost_inr)
               VALUES ({result_id}, {scenario_id}, {material_id}, {commodity_code},
                       {exposure_weight}, {observed_spend}, {exposed_spend}, {incremental_cost})""",
            {
                "result_id": result_id,
                "scenario_id": scenario_id,
                "material_id": material_id,
                "commodity_code": commodity_code,
                "exposure_weight": float(exposure_weight),
                "observed_spend": float(observed_spend or 0),
                "exposed_spend": float(exposed_spend or 0),
                "incremental_cost": float(incremental_cost or 0),
            },
        )

        results.append(
            ExposureResultSchema(
                material_id=material_id,
                material_name=material_name,
                commodity_code=commodity_code,
                commodity_name=commodity_code,
                exposure_weight=Decimal(str(exposure_weight)),
                mapping_confidence=confidence or "UNKNOWN",
                observed_spend_inr=Decimal(str(observed_spend or 0)),
                exposed_spend_inr=Decimal(str(exposed_spend or 0)),
                incremental_cost_inr=Decimal(str(incremental_cost or 0)),
                line_count=int(line_count) if line_count else 0,
                distinct_supplier_count=int(distinct_supplier_count) if distinct_supplier_count else 0,
            )
        )

    return results


def get_supplier_alternatives(
    conn: pyexasol.ExaConnection,
    material_id: str,
    required_qty: float,
    max_lead_time: float = 30.0,
    min_quality: float = 6.0,
) -> list[SupplierQuoteSchema]:
    sql = _load_query("supplier_comparison.sql")
    rows = conn.execute(
        sql,
        {
            "material_id": material_id,
            "required_qty": required_qty,
            "max_acceptable_lead_time": max_lead_time,
            "min_quality_score": min_quality,
        },
    ).fetchall()

    results: list[SupplierQuoteSchema] = []
    for r in rows:
        (
            quote_id, mat_id, mat_name,
            sup_id, sup_name, _city, _state,
            unit_price, min_order, max_cap, lead_time,
            quality, valid_until, notes,
            feasibility_status, price_rank,
        ) = r
        results.append(
            SupplierQuoteSchema(
                quote_id=quote_id,
                supplier_id=sup_id,
                supplier_name=sup_name,
                material_id=mat_id,
                material_name=mat_name,
                unit_price_inr=Decimal(str(unit_price)) if unit_price is not None else None,
                min_order_qty=Decimal(str(min_order)) if min_order is not None else None,
                max_capacity_qty=Decimal(str(max_cap)) if max_cap is not None else None,
                lead_time_days=int(lead_time) if lead_time is not None else None,
                quality_score=Decimal(str(quality)) if quality is not None else None,
                valid_until=valid_until,
                feasibility_status=feasibility_status,
                price_rank=int(price_rank),
                notes=notes,
            )
        )
    return results


def split_allocation_is_feasible(
    feasible: list[SupplierQuoteSchema],
    required_qty: Decimal,
) -> tuple[bool, str]:
    """Greedy cheapest-first allocation. Unknown capacity cannot prove a split."""
    if len(feasible) < 2:
        return False, "Fewer than two feasible suppliers."
    remaining = required_qty
    allocated: list[str] = []
    for alt in sorted(feasible, key=lambda a: a.unit_price_inr):
        if alt.max_capacity_qty is None:
            return False, f"{alt.supplier_name} has unknown capacity; split cannot be confirmed."
        moq = alt.min_order_qty or Decimal("0")
        cap = alt.max_capacity_qty
        if cap < moq:
            continue
        take = min(remaining, cap)
        if take < moq:
            continue
        remaining -= take
        allocated.append(f"{alt.supplier_name}={take}")
        if remaining <= 0:
            return True, "Allocated: " + "; ".join(allocated)
    return False, f"Combined feasible capacity cannot cover required quantity {required_qty}."


def generate_recommendation(
    conn: pyexasol.ExaConnection,
    scenario_id: str,
    material_id: str,
    exposure: ExposureResultSchema,
    alternatives: list[SupplierQuoteSchema],
    required_qty: float | None = None,
) -> RecommendationSchema:
    feasible = [a for a in alternatives if a.feasibility_status == "FEASIBLE"]
    unknown_critical = [
        a for a in alternatives
        if a.feasibility_status in {"CAPACITY_UNKNOWN", "PRICE_UNKNOWN", "QUALITY_UNKNOWN", "LEAD_TIME_UNKNOWN"}
    ]
    recommendation_id = str(uuid.uuid4())
    qty = Decimal(str(required_qty if required_qty is not None else get_historical_quantity(conn, material_id)))

    alternative_supplier_id = None
    estimated_saving_inr: Decimal | None = None
    saving_basis: str | None = None

    if exposure.observed_spend_inr == 0 and not alternatives:
        action_code = "NO_ACTION"
        action_summary = (
            f"No purchase evidence and no quotations for {material_id}. Nothing to act on."
        )
        evidence_summary = "Zero observed spend and no supplier quotations."
        confidence = "LOW"
    elif not feasible:
        action_code = "VERIFY_FIRST"
        if not alternatives:
            action_summary = (
                f"No supplier quotations found for {material_id}. "
                "Obtain at least two independent price quotes before acting."
            )
            evidence_summary = "No quotation data available. Cannot evaluate alternatives."
        else:
            reasons = list({a.feasibility_status for a in alternatives})
            action_summary = (
                f"All {len(alternatives)} alternative(s) failed feasibility checks "
                f"({', '.join(reasons)}). Verify constraints before proceeding."
            )
            evidence_summary = "\n".join(
                f"  {a.supplier_name}: {a.feasibility_status}" for a in alternatives
            )
        confidence = "LOW"
    else:
        priced = [a for a in feasible if a.unit_price_inr is not None]
        if not priced:
            action_code = "VERIFY_FIRST"
            action_summary = "Feasible suppliers were found but unit prices are unknown. Verify quotations."
            evidence_summary = "PRICE_UNKNOWN after feasibility filter."
            confidence = "LOW"
            conn.execute(
                """INSERT INTO RECOMMENDATIONS
                   (recommendation_id, scenario_id, material_id, action_code,
                    action_summary, confidence, requires_human_review,
                    alternative_supplier_id, estimated_saving_inr,
                    saving_basis, evidence_summary)
                   VALUES ({rid}, {sid}, {mid}, {action_code},
                           {action_summary}, {confidence}, {requires_review},
                           {alt_sup}, {saving}, {saving_basis}, {evidence})""",
                {
                    "rid": recommendation_id, "sid": scenario_id, "mid": material_id,
                    "action_code": action_code, "action_summary": action_summary,
                    "confidence": confidence, "requires_review": True,
                    "alt_sup": None, "saving": None, "saving_basis": None,
                    "evidence": evidence_summary,
                },
            )
            return RecommendationSchema(
                recommendation_id=recommendation_id, scenario_id=scenario_id,
                material_id=material_id, action_code=action_code,
                action_summary=action_summary, confidence=confidence,
                requires_human_review=True, alternative_supplier_id=None,
                estimated_saving_inr=None, saving_basis=None,
                evidence_summary=evidence_summary,
            )
        best = min(priced, key=lambda a: a.unit_price_inr or Decimal("0"))
        alternative_supplier_id = best.supplier_id

        current_row = conn.execute(
            """SELECT SUM(total_value_inr) / NULLIF(SUM(quantity), 0)
               FROM PURCHASE_LINES
               WHERE material_id = {mat_id} AND is_duplicate = FALSE""",
            {"mat_id": material_id},
        ).fetchone()
        current_avg_price = Decimal(str(current_row[0])) if current_row and current_row[0] else None

        if current_avg_price is not None and best.unit_price_inr < current_avg_price and qty > 0:
            price_diff = current_avg_price - best.unit_price_inr
            estimated_saving_inr = (price_diff * qty).quantize(Decimal("0.01"))
            saving_basis = (
                f"Calculated as (current volume-weighted avg price INR {current_avg_price:.2f} - "
                f"alternative price INR {best.unit_price_inr:.2f}) × "
                f"required volume {qty:.2f} units. "
                "Not guaranteed savings and not equal to hypothetical incremental commodity cost."
            )

        split_ok, split_note = split_allocation_is_feasible(feasible, qty if qty > 0 else Decimal("1"))

        if split_ok:
            action_code = "SPLIT_ORDERS"
            action_summary = (
                f"{len(feasible)} feasible suppliers can jointly cover the required quantity. "
                f"{split_note} Best unit price: {best.supplier_name} @ INR {best.unit_price_inr:,.2f}."
            )
            confidence = "HIGH"
        elif estimated_saving_inr and estimated_saving_inr > 0 and unknown_critical == []:
            action_code = "SWITCH_SUPPLIER"
            action_summary = (
                f"Switch to {best.supplier_name} @ INR {best.unit_price_inr:,.2f}/unit "
                f"is feasible. Indicative saving INR {estimated_saving_inr:,.2f} "
                "if historical volume is repriced at the quoted rate."
            )
            confidence = "MEDIUM"
        elif unknown_critical and not estimated_saving_inr:
            action_code = "VERIFY_FIRST"
            action_summary = (
                "Some quotations are missing capacity, quality, or lead-time evidence. "
                "Confirm those constraints before switching."
            )
            confidence = "LOW"
        else:
            action_code = "ACCEPT_COST"
            action_summary = (
                f"Lowest feasible alternative ({best.supplier_name}) is not cheaper than the incumbent, "
                "or savings cannot be calculated from known prices. "
                "Accept the modelled incremental cost or renegotiate."
            )
            confidence = "MEDIUM"

        infeasible_reasons = "\n".join(
            f"  {a.supplier_name}: {a.feasibility_status}"
            for a in alternatives if a.feasibility_status != "FEASIBLE"
        )
        evidence_summary = (
            f"Feasible alternatives: {len(feasible)}\n"
            f"Best price: {best.supplier_name} @ INR {best.unit_price_inr:,.2f}\n"
            f"Lead time: {best.lead_time_days} days | Quality: {best.quality_score}\n"
            f"Required qty used: {qty}\n"
            f"Rejected / unresolved alternatives:\n{infeasible_reasons or '  None'}"
        )

    conn.execute(
        """INSERT INTO RECOMMENDATIONS
           (recommendation_id, scenario_id, material_id, action_code,
            action_summary, confidence, requires_human_review,
            alternative_supplier_id, estimated_saving_inr,
            saving_basis, evidence_summary)
           VALUES ({rid}, {sid}, {mid}, {action_code},
                   {action_summary}, {confidence}, {requires_review},
                   {alt_sup}, {saving}, {saving_basis}, {evidence})""",
        {
            "rid": recommendation_id,
            "sid": scenario_id,
            "mid": material_id,
            "action_code": action_code,
            "action_summary": action_summary,
            "confidence": confidence,
            "requires_review": True,
            "alt_sup": alternative_supplier_id,
            "saving": float(estimated_saving_inr) if estimated_saving_inr is not None else None,
            "saving_basis": saving_basis,
            "evidence": evidence_summary,
        },
    )

    return RecommendationSchema(
        recommendation_id=recommendation_id,
        scenario_id=scenario_id,
        material_id=material_id,
        action_code=action_code,
        action_summary=action_summary,
        confidence=confidence,
        requires_human_review=True,
        alternative_supplier_id=alternative_supplier_id,
        estimated_saving_inr=estimated_saving_inr,
        saving_basis=saving_basis,
        evidence_summary=evidence_summary,
    )
