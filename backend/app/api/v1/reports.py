"""Report export endpoint."""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.db.connection import ExasolUnavailableError, get_db

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


@router.get("/export/{scenario_id}")
def export_report(scenario_id: str, fmt: str = "json") -> Response:
    """
    Export a scenario report.
    Formats: json (default) | csv
    JSON includes stored recommendation evidence and decisions. CSV is an
    exposure summary with scenario metadata only.
    """
    try:
        with get_db() as conn:
            # Scenario metadata
            sc = conn.execute(
                "SELECT * FROM SCENARIO_RUNS WHERE scenario_id = {sid}",
                {"sid": scenario_id},
            ).fetchone()
            if not sc:
                raise HTTPException(status_code=404, detail="Scenario not found")

            # Exposure results
            exp_rows = conn.execute(
                """SELECT er.material_id, m.material_name, er.commodity_code,
                          er.exposure_weight, er.observed_spend_inr,
                          er.exposed_spend_inr, er.incremental_cost_inr
                   FROM EXPOSURE_RESULTS er
                   JOIN MATERIALS m ON m.material_id = er.material_id
                   WHERE er.scenario_id = {sid}
                   ORDER BY er.incremental_cost_inr DESC""",
                {"sid": scenario_id},
            ).fetchall()

            # Recommendations
            rec_rows = conn.execute(
                """SELECT r.recommendation_id, r.material_id, r.action_code,
                          r.action_summary, r.confidence, r.alternative_supplier_id,
                          r.estimated_saving_inr, r.saving_basis, r.evidence_summary,
                          r.requires_human_review
                   FROM RECOMMENDATIONS r
                   WHERE r.scenario_id = {sid}""",
                {"sid": scenario_id},
            ).fetchall()

            # Decisions
            dec_rows = conn.execute(
                """SELECT de.decision_id, de.decision, de.decided_by,
                          de.decided_at, de.decision_notes
                   FROM DECISION_EVENTS de
                   JOIN RECOMMENDATIONS r ON r.recommendation_id = de.recommendation_id
                   WHERE r.scenario_id = {sid}
                   ORDER BY de.decided_at DESC""",
                {"sid": scenario_id},
            ).fetchall()

    except ExasolUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    report = {
        "report_generated_at": datetime.utcnow().isoformat() + "Z",
        "report_version": "1.0",
        "scenario": {
            "scenario_id": sc[0],
            "scenario_name": sc[1],
            "commodity_code": sc[2],
            "shock_pct": float(sc[3]),
            "shock_direction": sc[4],
            "analysis_period_start": str(sc[5]) if sc[5] else None,
            "analysis_period_end": str(sc[6]) if sc[6] else None,
        },
        "methodology": {
            "observed_spend": "SUM(total_value_inr) from PURCHASE_LINES for the analysis period",
            "exposed_spend": "observed_spend × material_commodity_exposure_weight",
            "incremental_cost": "exposed_spend × (shock_pct / 100)",
            "hhi": "SUM( (supplier_share_pct)^2 ) per material",
            "feasibility": "unit_price known AND qty >= MOQ AND qty <= capacity AND lead_time <= max AND quality >= min",
            "saving_estimate": "Calculated only when both current and alternative prices are known. "
                               "Not a forecast. Independent verification required.",
        },
        "exposure_results": [
            {
                "material_id": r[0], "material_name": r[1], "commodity_code": r[2],
                "exposure_weight": float(r[3]),
                "observed_spend_inr": float(r[4]), "exposed_spend_inr": float(r[5]),
                "incremental_cost_inr": float(r[6]),
            }
            for r in exp_rows
        ],
        "recommendations": [
            {
                "recommendation_id": r[0], "material_id": r[1], "action_code": r[2],
                "action_summary": r[3], "confidence": r[4],
                "alternative_supplier_id": r[5],
                "estimated_saving_inr": float(r[6]) if r[6] is not None else None,
                "saving_basis": r[7],
                "evidence_summary": r[8],
                "requires_human_review": bool(r[9]),
            }
            for r in rec_rows
        ],
        "decisions": [
            {
                "decision_id": r[0],
                "decision": r[1],
                "decided_by": r[2],
                "decided_at": str(r[3]),
                "decision_notes": r[4],
            }
            for r in dec_rows
        ],
        "limitations": [
            "All supplier and market data in this report is synthetic and for demonstration only.",
            "Exposure weights are based on publicly documented commodity-material relationships.",
            "Incremental cost estimates assume a linear price pass-through, which may not hold.",
            "Supplier capacity, lead time and quality data have not been independently verified.",
            "This report does not constitute financial, legal or procurement advice.",
            "Savings estimates are indicative only and depend on negotiated commercial terms.",
        ],
        "data_sources": {
            "purchase_data": "Synthetic dataset generated with seed=42 for reproducibility",
            "market_signals": "Simulated price series using geometric Brownian motion",
            "supplier_data": "Synthetic suppliers — not real businesses",
        },
    }

    if fmt == "csv":
        import csv
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["SupplyLens Report", report["report_generated_at"]])
        writer.writerow(["Scenario", sc[1], "Shock", f"{float(sc[3]):.1f}%", sc[4]])
        writer.writerow([])
        writer.writerow(["Material", "Commodity", "Weight", "Observed Spend INR",
                          "Exposed Spend INR", "Incremental Cost INR"])
        for r in exp_rows:
            writer.writerow([r[1], r[2], float(r[3]), float(r[4]), float(r[5]), float(r[6])])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report_{scenario_id}.csv"},
        )

    return Response(
        content=json.dumps(report, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=report_{scenario_id}.json"},
    )
