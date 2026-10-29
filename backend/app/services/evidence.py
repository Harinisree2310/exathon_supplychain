"""
Evidence Trace service.

Builds the chain:
  Market signal → Material mapping → Purchase evidence
  → Exposure calculation → Supplier comparison → Recommendation
"""
from __future__ import annotations

import logging
from typing import Any

import pyexasol  # type: ignore

from app.services.analytics import get_historical_quantity, get_supplier_alternatives

logger = logging.getLogger(__name__)


def build_evidence_trace(
    conn: pyexasol.ExaConnection,
    recommendation_id: str,
) -> dict[str, Any]:
    rec_row = conn.execute(
        """SELECT r.recommendation_id, r.scenario_id, r.material_id,
                  r.action_code, r.action_summary, r.confidence,
                  r.estimated_saving_inr, r.saving_basis, r.evidence_summary,
                  r.alternative_supplier_id,
                  m.material_name, m.unit_of_measure
           FROM RECOMMENDATIONS r
           JOIN MATERIALS m ON m.material_id = r.material_id
           WHERE r.recommendation_id = {rid}""",
        {"rid": recommendation_id},
    ).fetchone()

    if not rec_row:
        return {"error": f"Recommendation {recommendation_id} not found"}

    (rec_id, scenario_id, material_id, action_code, action_summary, confidence,
     saving_inr, saving_basis, evidence_summary, alt_sup_id, material_name, uom) = rec_row

    sc_row = conn.execute(
        """SELECT scenario_name, commodity_code, shock_pct, shock_direction,
                  analysis_period_start, analysis_period_end
           FROM SCENARIO_RUNS WHERE scenario_id = {sid}""",
        {"sid": scenario_id},
    ).fetchone()

    scenario_layer: dict[str, Any] = {}
    period_start = None
    period_end = None
    commodity_code = None
    if sc_row:
        period_start = sc_row[4]
        period_end = sc_row[5]
        commodity_code = sc_row[1]
        scenario_layer = {
            "scenario_id": scenario_id,
            "scenario_name": sc_row[0],
            "commodity_code": commodity_code,
            "shock_pct": float(sc_row[2]),
            "shock_direction": sc_row[3],
            "signed_shock_pct": (-abs(float(sc_row[2])) if str(sc_row[3]).upper() == "DOWN" else abs(float(sc_row[2]))),
            "analysis_period_start": str(period_start) if period_start else None,
            "analysis_period_end": str(period_end) if period_end else None,
            "assumption": "Shock percentage is a hypothetical assumption, not a market forecast.",
        }

    signal_layer: dict[str, Any] = {}
    if commodity_code:
        # Observation on or before the analysis period end — not a global "latest" substitute.
        if period_end is not None:
            sig_row = conn.execute(
                """SELECT signal_id, signal_date, price, currency, unit, signal_source
                   FROM MARKET_SIGNALS
                   WHERE commodity_code = {cc}
                     AND signal_date <= {as_of}
                   ORDER BY signal_date DESC
                   LIMIT 1""",
                {"cc": commodity_code, "as_of": str(period_end)},
            ).fetchone()
        else:
            sig_row = conn.execute(
                """SELECT signal_id, signal_date, price, currency, unit, signal_source
                   FROM V_LATEST_MARKET_SIGNAL
                   WHERE commodity_code = {cc}""",
                {"cc": commodity_code},
            ).fetchone()
        if sig_row:
            signal_layer = {
                "signal_id": sig_row[0],
                "signal_date": str(sig_row[1]),
                "price": float(sig_row[2]),
                "currency": sig_row[3],
                "unit": sig_row[4],
                "source": sig_row[5],
                "relevance": "Latest observation on or before analysis_period_end for this commodity.",
                "is_synthetic": True,
            }
        else:
            signal_layer = {
                "unknown": True,
                "message": "No market observation found on or before the analysis period end.",
            }

    map_sql = """SELECT map_id, commodity_code, commodity_name,
                        exposure_weight, mapping_basis, confidence
                 FROM MATERIAL_COMMODITY_MAP
                 WHERE material_id = {mid}"""
    params: dict[str, Any] = {"mid": material_id}
    if commodity_code:
        map_sql += " AND commodity_code = {cc}"
        params["cc"] = commodity_code
    map_rows = conn.execute(map_sql, params).fetchall()
    mapping_layer = [
        {
            "map_id": r[0],
            "commodity_code": r[1],
            "commodity_name": r[2],
            "exposure_weight": float(r[3]),
            "mapping_basis": r[4],
            "confidence": r[5],
            "used_in_this_scenario": True,
        }
        for r in map_rows
    ]

    purchase_sql = """
        SELECT pl.line_id, pl.po_number, pl.purchase_date,
               pl.quantity, pl.unit_price_inr, pl.total_value_inr,
               s.supplier_name
        FROM PURCHASE_LINES pl
        JOIN SUPPLIERS s ON s.supplier_id = pl.supplier_id
        WHERE pl.material_id = {mid} AND pl.is_duplicate = FALSE
    """
    purchase_params: dict[str, Any] = {"mid": material_id}
    if period_start and period_end:
        purchase_sql += " AND pl.purchase_date BETWEEN {ps} AND {pe}"
        purchase_params["ps"] = str(period_start)
        purchase_params["pe"] = str(period_end)
    purchase_sql += " ORDER BY pl.purchase_date DESC LIMIT 25"
    pl_rows = conn.execute(purchase_sql, purchase_params).fetchall()
    purchase_layer = [
        {
            "line_id": r[0],
            "po_number": r[1],
            "purchase_date": str(r[2]),
            "quantity": float(r[3]),
            "unit_price_inr": float(r[4]),
            "total_value_inr": float(r[5]),
            "supplier_name": r[6],
        }
        for r in pl_rows
    ]

    exp_row = conn.execute(
        """SELECT result_id, exposure_weight,
                  observed_spend_inr, exposed_spend_inr, incremental_cost_inr
           FROM EXPOSURE_RESULTS
           WHERE scenario_id = {sid} AND material_id = {mid}
           LIMIT 1""",
        {"sid": scenario_id, "mid": material_id},
    ).fetchone()
    exposure_layer: dict[str, Any] = {}
    if exp_row:
        exposure_layer = {
            "result_id": exp_row[0],
            "exposure_weight": float(exp_row[1]),
            "observed_spend_inr": float(exp_row[2]),
            "exposed_spend_inr": float(exp_row[3]),
            "incremental_cost_inr": float(exp_row[4]),
            "formula": (
                "exposed_spend = observed_spend × exposure_weight; "
                "incremental_cost = exposed_spend × (signed_shock_pct / 100)"
            ),
        }
    else:
        exposure_layer = {"unknown": True, "message": "No persisted exposure result for this scenario and material."}

    qty = get_historical_quantity(conn, material_id) or 1.0
    alternatives = get_supplier_alternatives(conn, material_id, qty)
    supplier_layer = [
        {
            "quote_id": a.quote_id,
            "supplier_name": a.supplier_name,
            "unit_price_inr": float(a.unit_price_inr) if a.unit_price_inr is not None else None,
            "min_order_qty": float(a.min_order_qty) if a.min_order_qty is not None else None,
            "max_capacity_qty": float(a.max_capacity_qty) if a.max_capacity_qty is not None else None,
            "lead_time_days": a.lead_time_days,
            "quality_score": float(a.quality_score) if a.quality_score is not None else None,
            "valid_until": str(a.valid_until) if a.valid_until else None,
            "feasibility_status": a.feasibility_status,
            "used_as_recommended_alternative": a.supplier_id == alt_sup_id,
        }
        for a in alternatives
    ]

    return {
        "recommendation_id": rec_id,
        "material_id": material_id,
        "material_name": material_name,
        "unit_of_measure": uom,
        "action_code": action_code,
        "action_summary": action_summary,
        "confidence": confidence,
        "estimated_saving_inr": float(saving_inr) if saving_inr else None,
        "saving_basis": saving_basis,
        "evidence_summary": evidence_summary,
        "evidence_chain": {
            "1_scenario": scenario_layer,
            "2_market_signal": signal_layer,
            "3_material_mapping": mapping_layer,
            "4_purchase_evidence": purchase_layer,
            "5_exposure_calculation": exposure_layer,
            "6_supplier_alternatives": supplier_layer,
        },
        "disclaimer": (
            "All supplier data is synthetic. Market signals are simulated. "
            "No recommendation should be acted upon without independent verification. "
            "This tool does not place orders or initiate procurement actions."
        ),
    }
