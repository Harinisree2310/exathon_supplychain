"""
API integration tests using FastAPI TestClient with a mocked database.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend is on the path before any imports
sys.path.insert(0, str(Path(__file__).parents[1]))

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """TestClient with Exasol dependency mocked out."""
    import app.db.connection as _conn_module  # ensure module loaded

    with patch.object(_conn_module, "_make_connection") as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn_factory.return_value = mock_conn

        # Default responses for common queries
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.execute.return_value.fetchone.return_value = (1,)
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)

        from app.main import app
        with TestClient(app) as c:
            yield c


class TestHealthEndpoints:
    def test_root(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "SupplyLens"

    def test_health_returns_status(self, client: TestClient) -> None:
        with patch("app.api.v1.health.probe_connection") as mock_probe:
            from app.db.connection import DatabaseStatus
            mock_probe.return_value = DatabaseStatus.DEGRADED
            resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "database" in data
        assert data["database"] == "degraded"

    def test_health_reports_degraded_not_silently_ok(self, client: TestClient) -> None:
        """
        Critical: health endpoint must never report 'connected'
        when the database is unreachable.
        """
        with patch("app.api.v1.health.probe_connection") as mock_probe:
            from app.db.connection import DatabaseStatus
            mock_probe.return_value = DatabaseStatus.DEGRADED
            resp = client.get("/health")
        assert resp.json()["database"] != "connected"


class TestDataEndpoints:
    def test_quality_endpoint_returns_schema(self, client: TestClient) -> None:
        with patch("app.api.v1.data.get_data_quality") as mock_quality:
            from app.schemas.common import DataQualitySummarySchema
            mock_quality.return_value = DataQualitySummarySchema(
                total_materials=6, total_suppliers=7,
                total_purchase_lines=72, total_market_signals=1274,
                materials_with_mapping=6, materials_without_mapping=0,
                stale_signal_count=0, incomplete_quotations=0,
            )
            with patch("app.api.v1.data.get_db"):
                resp = client.get("/api/v1/data/quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_materials"] == 6

    def test_purchase_template_is_csv(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/template/purchases")
        assert resp.status_code == 200
        assert "po_number" in resp.text
        assert "material_code" in resp.text

    def test_upload_rejects_unsupported_format(self, client: TestClient) -> None:
        with patch("app.api.v1.data.get_db"):
            resp = client.post(
                "/api/v1/data/upload/purchases",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
            )
        assert resp.status_code == 400

    def test_upload_rejects_oversized_file_before_ingestion(self, client: TestClient) -> None:
        with patch("app.api.v1.data.settings.max_upload_bytes", 4), patch(
            "app.api.v1.data.ingest_purchase_csv"
        ) as ingest:
            resp = client.post(
                "/api/v1/data/upload/purchases",
                files={"file": ("purchases.csv", b"12345", "text/csv")},
            )
        assert resp.status_code == 413
        ingest.assert_not_called()

    def test_upload_rejects_missing_columns(self, client: TestClient) -> None:
        csv_content = b"po_number,purchase_date\nPO-001,2026-01-05\n"
        with patch("app.api.v1.data.get_db"):
            resp = client.post(
                "/api/v1/data/upload/purchases",
                files={"file": ("purchases.csv", csv_content, "text/csv")},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "Missing required columns" in resp.json()["data"]["error"]


class TestScenarioEndpoints:
    def test_create_scenario_validates_shock_pct(self, client: TestClient) -> None:
        """Shock > 100% must be rejected."""
        payload = {
            "scenario_name": "Test",
            "commodity_code": "BRENT_CRUDE",
            "shock_pct": 150.0,  # invalid
            "shock_direction": "UP",
            "analysis_period_start": "2025-07-01",
            "analysis_period_end": "2026-01-01",
        }
        with patch("app.api.v1.analytics.get_db"):
            resp = client.post("/api/v1/analytics/scenarios", json=payload)
        assert resp.status_code == 422

    def test_create_scenario_allows_zero_shock(self, client: TestClient) -> None:
        from datetime import date, datetime

        scenario_row = (
            "scenario-zero",
            "Zero Shock",
            "BRENT_CRUDE",
            Decimal("0"),
            "UP",
            date(2025, 7, 1),
            date(2026, 1, 1),
            datetime(2026, 10, 28),
        )
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = scenario_row
        mock_db = MagicMock()
        mock_db.__enter__.return_value = mock_conn

        with patch("app.api.v1.analytics.get_db", return_value=mock_db):
            resp = client.post(
                "/api/v1/analytics/scenarios",
                json={
                    "scenario_name": "Zero Shock",
                    "commodity_code": "BRENT_CRUDE",
                    "shock_pct": 0,
                    "shock_direction": "UP",
                    "analysis_period_start": "2025-07-01",
                    "analysis_period_end": "2026-01-01",
                },
            )

        assert resp.status_code == 201
        assert Decimal(resp.json()["shock_pct"]) == Decimal("0")

    def test_create_scenario_validates_direction(self, client: TestClient) -> None:
        payload = {
            "scenario_name": "Test",
            "commodity_code": "LME_COPPER",
            "shock_pct": 10.0,
            "shock_direction": "SIDEWAYS",  # invalid
            "analysis_period_start": "2025-07-01",
            "analysis_period_end": "2026-01-01",
        }
        with patch("app.api.v1.analytics.get_db"):
            resp = client.post("/api/v1/analytics/scenarios", json=payload)
        assert resp.status_code == 422


class TestMarketSignalEndpoints:
    def test_market_signals_use_schema_column_and_return_numeric_price(
        self, client: TestClient
    ) -> None:
        from datetime import date

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("signal-1", "BRENT_CRUDE", date(2026, 1, 1), Decimal("81.25"), "USD", "barrel", "SYNTHETIC")
        ]
        mock_db = MagicMock()
        mock_db.__enter__.return_value = conn

        with patch("app.api.v1.analytics.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/analytics/market-signals?commodity_code=BRENT_CRUDE"
            )

        assert response.status_code == 200
        signal = response.json()[0]
        assert signal["source"] == "SYNTHETIC"
        assert signal["price"] == 81.25
        assert isinstance(signal["price"], (int, float))
        assert "signal_source FROM MARKET_SIGNALS" in conn.execute.call_args.args[0]
        assert "LIMIT 180" in conn.execute.call_args.args[0]


class TestSupplierEndpoints:
    def test_list_suppliers_avoids_reserved_state_alias(self, client: TestClient) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            ("S001", "Supplier One", "Pune", "Maharashtra", "Tier 1", 12, Decimal("0.9"))
        ]
        mock_db = MagicMock()
        mock_db.__enter__.return_value = mock_conn

        with patch("app.api.v1.analytics.get_db", return_value=mock_db):
            resp = client.get("/api/v1/analytics/suppliers")

        assert resp.status_code == 200
        assert resp.json()[0]["state"] == "Maharashtra"
        assert isinstance(resp.json()[0]["quality_score"], (int, float))
        assert "supplier_state AS state" not in mock_conn.execute.call_args.args[0]


class TestDecisionEndpoints:
    def test_decision_validates_decision_value(self, client: TestClient) -> None:
        payload = {
            "recommendation_id": "some-uuid",
            "decision": "MAYBE",  # not in enum
            "decided_by": "user1",
        }
        with patch("app.api.v1.analytics.get_db"):
            resp = client.post("/api/v1/analytics/decisions", json=payload)
        assert resp.status_code == 422

    def test_decision_requires_decided_by(self, client: TestClient) -> None:
        payload = {
            "recommendation_id": "some-uuid",
            "decision": "APPROVED",
        }
        with patch("app.api.v1.analytics.get_db"):
            resp = client.post("/api/v1/analytics/decisions", json=payload)
        assert resp.status_code == 422


class TestRecommendationEndpoints:
    def test_requested_quantity_is_used_for_recommendation(self, client: TestClient) -> None:
        from app.schemas.common import (
            ExposureResultSchema,
            RecommendationSchema,
        )

        exposure = ExposureResultSchema(
            material_id="M001",
            material_name="Steel",
            commodity_code="BRENT_CRUDE",
            commodity_name="Brent Crude",
            exposure_weight=Decimal("0.3"),
            mapping_confidence="HIGH",
            observed_spend_inr=Decimal("1000"),
            exposed_spend_inr=Decimal("300"),
            incremental_cost_inr=Decimal("45"),
        )
        recommendation = RecommendationSchema(
            recommendation_id="recommendation-id",
            scenario_id="scenario-id",
            material_id="M001",
            action_code="VERIFY_FIRST",
            action_summary="Verify supplier constraints.",
            confidence="LOW",
            requires_human_review=True,
        )
        with patch("app.api.v1.analytics.svc.calculate_exposure", return_value=[exposure]), patch(
            "app.api.v1.analytics.svc.get_supplier_alternatives", return_value=[]
        ), patch(
            "app.api.v1.analytics.svc.generate_recommendation",
            return_value=recommendation,
        ) as generate:
            resp = client.post(
                "/api/v1/analytics/recommendations",
                params={
                    "scenario_id": "scenario-id",
                    "material_id": "M001",
                    "required_qty": 1234,
                },
            )

        assert resp.status_code == 201
        assert generate.call_args.args[-1] == 1234


class TestEvidenceEndpoints:
    def test_missing_recommendation_returns_not_found(self, client: TestClient) -> None:
        with patch("app.api.v1.analytics.get_db"), patch(
            "app.api.v1.analytics.build_evidence_trace",
            return_value={"error": "Recommendation missing not found"},
        ):
            resp = client.get("/api/v1/analytics/evidence/missing")
        assert resp.status_code == 404


class TestReportEndpoints:
    def test_json_report_includes_recommendation_evidence_and_decision_notes(
        self, client: TestClient
    ) -> None:
        from datetime import date
        from unittest.mock import MagicMock

        scenario_result = MagicMock()
        scenario_result.fetchone.return_value = (
            "scenario-id", "Test scenario", "BRENT_CRUDE", 15.0, "UP",
            date(2025, 7, 1), date(2026, 1, 1),
        )
        exposure_result = MagicMock()
        exposure_result.fetchall.return_value = []
        recommendation_result = MagicMock()
        recommendation_result.fetchall.return_value = [
            (
                "recommendation-id", "M001", "VERIFY_FIRST", "Verify capacity.",
                "LOW", None, None, None, "Quote capacity is unknown.", True,
            )
        ]
        decision_result = MagicMock()
        decision_result.fetchall.return_value = [
            ("decision-id", "DEFERRED", "Procurement", None, "Recheck capacity."),
        ]
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.__exit__.return_value = False
        conn.execute.side_effect = [
            scenario_result, exposure_result, recommendation_result, decision_result,
        ]

        with patch("app.api.v1.reports.get_db", return_value=conn):
            resp = client.get("/api/v1/reports/export/scenario-id")

        assert resp.status_code == 200
        report = resp.json()
        assert report["recommendations"][0]["evidence_summary"] == "Quote capacity is unknown."
        assert report["recommendations"][0]["requires_human_review"] is True
        assert report["decisions"][0]["decision_notes"] == "Recheck capacity."
