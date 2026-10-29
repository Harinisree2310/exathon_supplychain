"""
Tests for synthetic data generation.
These do not require a live database — they validate the Python-computed
expected outputs that are later compared against Exasol results.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

SYNTHETIC_DIR = Path(__file__).parents[2] / "data" / "synthetic"


class TestSyntheticDataGeneration:
    def test_generate_creates_all_csv_files(self, tmp_path: Path) -> None:
        """Running generate_dataset.py should produce required CSV files."""
        result = subprocess.run(
            [sys.executable, str(SYNTHETIC_DIR / "generate_dataset.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Generator failed: {result.stderr}"
        for fname in [
            "suppliers.csv", "materials.csv", "commodity_map.csv",
            "market_signals.csv", "purchase_lines.csv",
            "supplier_quotations.csv", "scenario_runs.csv",
        ]:
            assert (SYNTHETIC_DIR / fname).exists(), f"Missing: {fname}"

    def test_purchase_lines_count(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "purchase_lines.csv")
        # 6 materials × up to 7 suppliers × 6 months = should be > 60 rows
        assert len(df) > 60

    def test_suppliers_count(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "suppliers.csv")
        assert len(df) >= 5

    def test_materials_count(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "materials.csv")
        assert len(df) >= 6

    def test_market_signals_cover_all_commodities(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "market_signals.csv")
        expected_commodities = {
            "LME_HRC_STEEL", "COKING_COAL", "NAPHTHA_SPOT",
            "BRENT_CRUDE", "LME_COPPER", "PALM_OIL_BMD", "LME_ALUMINIUM",
        }
        actual = set(df["commodity_code"].unique())
        assert expected_commodities == actual

    def test_m001_is_concentrated(self, expected_outputs: dict) -> None:
        """M001 (Steel Coil) must be highly concentrated (HHI > 2500)."""
        assert expected_outputs["m001_hhi"] > 2500
        assert expected_outputs["m001_hhi_level"] == "HIGH"
        assert expected_outputs["m001_dominant_supplier"] == "S001"
        assert expected_outputs["m001_dominant_share_pct"] > 88.0

    def test_sc001_incremental_cost_is_positive(self, expected_outputs: dict) -> None:
        """Brent Crude +15% shock should produce positive incremental costs."""
        assert expected_outputs["sc001_total_incremental"] > 0

    def test_total_spend_per_material_non_zero(self, expected_outputs: dict) -> None:
        for mat_id, spend in expected_outputs["total_spend_by_material"].items():
            assert spend > 0, f"{mat_id} has zero spend"

    def test_commodity_map_weights_sum_to_one(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "commodity_map.csv")
        totals = df.groupby("material_id")["exposure_weight"].sum()
        for mat_id, total in totals.items():
            assert abs(total - 1.0) < 0.001, (
                f"Material {mat_id} weights sum to {total:.4f}, expected 1.0"
            )

    def test_no_duplicate_po_numbers(self) -> None:
        df = pd.read_csv(SYNTHETIC_DIR / "purchase_lines.csv")
        assert df["po_number"].is_unique, "Duplicate PO numbers found"

    def test_quotation_has_rejected_alternative(self) -> None:
        """Q005 (NorthWest Plastics, M002) should be rejected by capacity constraint."""
        df = pd.read_csv(SYNTHETIC_DIR / "supplier_quotations.csv")
        q005 = df[df["quote_id"] == "Q005"].iloc[0]
        # 5000 kg required monthly; max_capacity = 1500 → rejected
        assert q005["max_capacity_qty"] < 5000.0

    def test_demo_has_current_supplier_quotes(self) -> None:
        """At least one demo quote must remain valid for supplier feasibility."""
        df = pd.read_csv(SYNTHETIC_DIR / "supplier_quotations.csv")
        valid_until = pd.to_datetime(df["valid_until"], errors="coerce")
        assert (valid_until >= pd.Timestamp.now().normalize()).any()


class TestIngestionLogic:
    def test_database_probe_uses_application_settings(self) -> None:
        from types import SimpleNamespace
        from unittest.mock import patch

        from tests.conftest import _can_reach_exasol

        settings = SimpleNamespace(exasol_host="db.example", exasol_port=8564)
        with patch("app.core.config.get_settings", return_value=settings), patch(
            "socket.create_connection"
        ) as connect:
            assert _can_reach_exasol()
        connect.assert_called_once_with(("db.example", 8564), timeout=2)

    def test_normalise_text(self) -> None:
        from app.services.ingestion import _normalise_text
        assert _normalise_text("  hot rolled   Steel ") == "HOT ROLLED STEEL"
        assert _normalise_text(None) == ""

    def test_row_fingerprint_is_deterministic(self) -> None:
        from app.services.ingestion import _row_fingerprint
        import pandas as pd
        row = pd.Series({
            "po_number": "PO-001",
            "purchase_date": "2026-01-05",
            "material_code": "HR-STEEL-COIL",
            "supplier_name": "AgroMet",
            "quantity": "15.0",
        })
        fp1 = _row_fingerprint(row)
        fp2 = _row_fingerprint(row)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_different_rows_produce_different_fingerprints(self) -> None:
        from app.services.ingestion import _row_fingerprint
        import pandas as pd
        row1 = pd.Series({"po_number": "PO-001", "purchase_date": "2026-01-05",
                          "material_code": "HR-STEEL-COIL", "supplier_name": "A", "quantity": "10"})
        row2 = pd.Series({"po_number": "PO-002", "purchase_date": "2026-01-05",
                          "material_code": "HR-STEEL-COIL", "supplier_name": "A", "quantity": "10"})
        assert _row_fingerprint(row1) != _row_fingerprint(row2)
