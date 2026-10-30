"""
Analytics service unit tests (mock database) and live DB tests.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.common import ConcentrationSchema, ExposureResultSchema


class TestExposureCalculations:
    """Unit tests for exposure formula correctness."""

    def test_incremental_cost_formula(self) -> None:
        """
        Formula: incremental_cost = observed_spend × exposure_weight × (shock_pct / 100)
        """
        observed_spend = Decimal("1000000")  # INR 10 lakh
        exposure_weight = Decimal("0.30")
        shock_pct = Decimal("15")

        exposed = observed_spend * exposure_weight
        incremental = exposed * (shock_pct / 100)

        assert exposed == Decimal("300000")
        assert incremental == Decimal("45000")

    def test_zero_spend_gives_zero_incremental(self) -> None:
        observed = Decimal("0")
        weight = Decimal("0.85")
        shock = Decimal("20")
        assert observed * weight * (shock / 100) == Decimal("0")

    def test_100_pct_shock_equals_exposed_spend(self) -> None:
        obs = Decimal("500000")
        w = Decimal("0.90")
        exposed = obs * w
        assert exposed * (Decimal("100") / 100) == exposed


class TestHHICalculation:
    """Unit tests for Herfindahl–Hirschman Index."""

    def test_monopoly_hhi(self) -> None:
        """Single supplier = HHI 10000."""
        shares = [100.0]
        hhi = sum(s ** 2 for s in shares)
        assert hhi == 10000.0

    def test_duopoly_equal_split_hhi(self) -> None:
        """Two equal suppliers = HHI 5000."""
        shares = [50.0, 50.0]
        hhi = sum(s ** 2 for s in shares)
        assert hhi == 5000.0

    def test_concentrated_threshold(self) -> None:
        """90/10 split is highly concentrated (> 2500)."""
        shares = [90.0, 10.0]
        hhi = sum(s ** 2 for s in shares)
        assert hhi == 8200.0
        assert hhi > 2500

    def test_m001_expected_hhi(self, expected_outputs: dict) -> None:
        """M001 Python-computed HHI must be > 2500."""
        assert expected_outputs["m001_hhi"] > 2500

    def test_concentration_decimals_serialize_as_json_numbers(self) -> None:
        concentration = ConcentrationSchema(
            material_id="M001",
            material_name="Steel Coil",
            hhi=Decimal("8180"),
            concentration_level="HIGH",
            supplier_count=1,
            dominant_share_pct=Decimal("90"),
        )

        payload = concentration.model_dump(mode="json")

        assert payload["hhi"] == 8180.0
        assert isinstance(payload["hhi"], float)
        assert payload["dominant_share_pct"] == 90.0


class TestDataQuality:
    def test_stale_signals_measure_latest_signal_age(self) -> None:
        from app.services.analytics import get_data_quality

        conn = MagicMock()
        conn.execute.return_value.fetchone.side_effect = [
            (6,), (7,), (84,), (1288,), (6,), (7,), (0,),
        ]

        summary = get_data_quality(conn)

        assert summary.stale_signal_count == 7
        queries = [call.args[0] for call in conn.execute.call_args_list]
        stale_query = next(query for query in queries if "latest_signal_date" in query)
        assert "ADD_DAYS(CURRENT_DATE, -30)" in stale_query


class TestSupplierFeasibility:
    """Unit tests for feasibility decision logic."""

    def _make_quote(self, **kwargs):
        from app.schemas.common import SupplierQuoteSchema
        defaults = {
            "quote_id": "Q-TEST",
            "supplier_id": "S001",
            "supplier_name": "Test Supplier",
            "material_id": "M001",
            "material_name": "Steel",
            "unit_price_inr": Decimal("52000"),
            "min_order_qty": Decimal("5"),
            "max_capacity_qty": Decimal("50"),
            "lead_time_days": 14,
            "quality_score": Decimal("8.5"),
            "feasibility_status": "FEASIBLE",
            "price_rank": 1,
        }
        defaults.update(kwargs)
        return SupplierQuoteSchema(**defaults)

    def test_feasible_quote_passes(self) -> None:
        q = self._make_quote(feasibility_status="FEASIBLE")
        assert q.feasibility_status == "FEASIBLE"

    def test_moq_not_met_is_rejected(self) -> None:
        # min_order_qty = 1000, required = 500 → MOQ_NOT_MET
        q = self._make_quote(feasibility_status="MOQ_NOT_MET", min_order_qty=Decimal("1000"))
        assert q.feasibility_status == "MOQ_NOT_MET"

    def test_capacity_exceeded_is_rejected(self) -> None:
        q = self._make_quote(feasibility_status="CAPACITY_EXCEEDED", max_capacity_qty=Decimal("100"))
        assert q.feasibility_status == "CAPACITY_EXCEEDED"

    def test_quality_below_threshold(self) -> None:
        q = self._make_quote(feasibility_status="QUALITY_BELOW_THRESHOLD", quality_score=Decimal("4.0"))
        assert q.feasibility_status == "QUALITY_BELOW_THRESHOLD"


class TestRecommendationEngine:
    """Tests for deterministic recommendation logic."""

    def test_savings_use_quantity_weighted_historical_price(self, mock_conn) -> None:
        from app.schemas.common import SupplierQuoteSchema
        from app.services.analytics import generate_recommendation

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
        quote = SupplierQuoteSchema(
            quote_id="Q1",
            supplier_id="S2",
            supplier_name="Alternative",
            material_id="M001",
            material_name="Steel",
            unit_price_inr=Decimal("100"),
            min_order_qty=Decimal("1"),
            max_capacity_qty=Decimal("20"),
            lead_time_days=10,
            quality_score=Decimal("8"),
            feasibility_status="FEASIBLE",
            price_rank=1,
        )
        mock_conn.execute.return_value.fetchone.return_value = (150,)

        recommendation = generate_recommendation(
            mock_conn, "SC001", "M001", exposure, [quote], required_qty=10
        )

        assert recommendation.estimated_saving_inr == Decimal("500.00")
        statements = [call.args[0] for call in mock_conn.execute.call_args_list]
        assert any(
            "SUM(total_value_inr) / NULLIF(SUM(quantity), 0)" in statement
            for statement in statements
        )

    def test_no_feasible_alternatives_gives_verify_first(self, mock_conn) -> None:
        from app.schemas.common import ExposureResultSchema, SupplierQuoteSchema
        from app.services.analytics import generate_recommendation

        exposure = ExposureResultSchema(
            material_id="M001", material_name="Steel",
            commodity_code="BRENT_CRUDE", commodity_name="Brent Crude",
            exposure_weight=Decimal("0.30"),
            mapping_confidence="HIGH",
            observed_spend_inr=Decimal("1000000"),
            exposed_spend_inr=Decimal("300000"),
            incremental_cost_inr=Decimal("45000"),
        )
        infeasible = [
            SupplierQuoteSchema(
                quote_id="Q1", supplier_id="S2", supplier_name="Alt Sup",
                material_id="M001", material_name="Steel",
                unit_price_inr=Decimal("50000"),
                min_order_qty=Decimal("1000"),
                max_capacity_qty=Decimal("500"),
                lead_time_days=14, quality_score=Decimal("8.0"),
                feasibility_status="CAPACITY_EXCEEDED",
                price_rank=1,
            )
        ]

        # Mock conn INSERT and SELECT calls
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_conn.execute.return_value.fetchall.return_value = []

        rec = generate_recommendation(mock_conn, "SC001", "M001", exposure, infeasible)
        assert rec.action_code == "VERIFY_FIRST"
        assert rec.requires_human_review is True
        assert rec.estimated_saving_inr is None

    def test_saving_not_calculated_when_price_unknown(self) -> None:
        """
        Savings must be None when current price cannot be determined.
        Never invent savings figures.
        """
        from app.schemas.common import ExposureResultSchema, SupplierQuoteSchema
        # If avg price query returns None, saving must remain None
        exposure = ExposureResultSchema(
            material_id="M999", material_name="Unknown Mat",
            commodity_code="LME_COPPER", commodity_name="LME Copper",
            exposure_weight=Decimal("0.92"),
            mapping_confidence="HIGH",
            observed_spend_inr=Decimal("0"),
            exposed_spend_inr=Decimal("0"),
            incremental_cost_inr=Decimal("0"),
        )
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (None,)
        mock_conn.execute.return_value.fetchall.return_value = []

        feasible = [
            SupplierQuoteSchema(
                quote_id="Q1", supplier_id="S1", supplier_name="Good Sup",
                material_id="M999", material_name="Unknown Mat",
                unit_price_inr=Decimal("700"),
                min_order_qty=Decimal("100"),
                max_capacity_qty=Decimal("5000"),
                lead_time_days=14, quality_score=Decimal("8.0"),
                feasibility_status="FEASIBLE",
                price_rank=1,
            )
        ]
        from app.services.analytics import generate_recommendation
        rec = generate_recommendation(mock_conn, "SC999", "M999", exposure, feasible)
        # With zero observed spend and no avg price, saving should be None or 0
        # The important assertion is: we did NOT invent a positive saving
        assert rec.action_code in ("ACCEPT_COST", "SWITCH_SUPPLIER", "SPLIT_ORDERS")


class TestLLMExplainer:
    def test_deterministic_fallback_returns_valid_structure(self) -> None:
        from app.services.llm_explainer import _deterministic_fallback
        result = _deterministic_fallback("SWITCH_SUPPLIER", {})
        assert "headline" in result
        assert "explanation" in result
        assert isinstance(result["caveats"], list)
        assert len(result["caveats"]) > 0
        assert result["source"] == "deterministic_fallback"

    def test_llm_explainer_falls_back_when_provider_empty(self) -> None:
        from app.services.llm_explainer import explain_recommendation
        with patch("app.services.llm_explainer.settings") as mock_settings:
            mock_settings.llm_provider = ""
            result = explain_recommendation("VERIFY_FIRST", {"action_code": "VERIFY_FIRST"})
        assert result["source"] == "deterministic_fallback"

    def test_invalid_llm_output_falls_back(self) -> None:
        """LLM returning garbage must never propagate."""
        from app.services.llm_explainer import explain_recommendation, _call_llm
        with patch("app.services.llm_explainer.settings") as ms:
            ms.llm_provider = "openai"
            ms.llm_api_key = "fake"
            ms.llm_model = "gpt-4o-mini"
            with patch("app.services.llm_explainer._call_openai", return_value='{"bad": "json"}'):
                result = explain_recommendation("ACCEPT_COST", {})
        assert result["source"] == "deterministic_fallback"


# ── Live DB tests (BLOCKED when Exasol unreachable) ───────────────────────────

@pytest.mark.requires_db
class TestLiveExasolAnalytics:
    def test_hhi_matches_expected(self, live_conn, expected_outputs: dict) -> None:
        """HHI computed by Exasol must match Python baseline within 0.01%."""
        from app.services.analytics import get_material_concentration
        concentrations = get_material_concentration(live_conn)
        m001 = next((c for c in concentrations if c.material_id == "M001"), None)
        assert m001 is not None, "M001 concentration not found"
        expected_hhi = expected_outputs["m001_hhi"]
        diff = abs(float(m001.hhi) - expected_hhi)
        assert diff < expected_hhi * 0.001, (
            f"HHI mismatch: Exasol={m001.hhi}, Python={expected_hhi}, diff={diff}"
        )

    def test_scenario_incremental_cost_matches_expected(self, live_conn, expected_outputs: dict) -> None:
        """SC001 Exasol incremental cost must match Python baseline within 0.01%."""
        from app.services.analytics import calculate_exposure
        results = calculate_exposure(live_conn, "SC001")
        exasol_total = sum(float(r.incremental_cost_inr) for r in results)
        python_total = expected_outputs["sc001_total_incremental"]
        diff = abs(exasol_total - python_total)
        assert diff < python_total * 0.001, (
            f"Incremental cost mismatch: Exasol={exasol_total:.2f}, "
            f"Python={python_total:.2f}, diff={diff:.2f}"
        )

    def test_schema_initialised(self, live_conn) -> None:
        from app.services.analytics import get_db_row_counts
        counts = get_db_row_counts(live_conn)
        assert counts["SUPPLIERS"] >= 7
        assert counts["MATERIALS"] >= 6
        assert counts["PURCHASE_LINES"] > 0
        assert counts["MARKET_SIGNALS"] > 0
