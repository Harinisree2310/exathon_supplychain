"""
SupplyLens Synthetic Dataset Generator
=======================================
Generates a deterministic, labelled dataset that exercises every
analytical feature of SupplyLens.

Key design decisions:
- Seeds the RNG so every run produces identical data.
- All monetary values in INR.
- Includes at least one concentrated supplier dependency (HHI > 2500).
- Includes at least one rejected alternative (MOQ not met).
- Includes one scenario requiring further verification.
- Documents exactly what the expected analytical outputs are
  so tests can compare Exasol results against Python-calculated baselines.

Run directly:
    python data/synthetic/generate_dataset.py

Output: data/synthetic/*.csv
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEED = 42
RNG = np.random.default_rng(SEED)

OUT_DIR = Path(__file__).parent
EXPECTED_DIR = OUT_DIR.parent / "expected"
EXPECTED_DIR.mkdir(exist_ok=True)

START_DATE = date(2025, 7, 1)
END_DATE = date(2026, 1, 1)  # 6 months


# ── 1. Suppliers ──────────────────────────────────────────────────────────────
SUPPLIERS = [
    {"supplier_id": "S001", "supplier_name": "AgroMet Industries",      "city": "Mumbai",    "state": "Maharashtra", "lead_time_days": 14, "quality_score": 8.5, "supplier_tier": "PREFERRED"},
    {"supplier_id": "S002", "supplier_name": "SteelCraft Pvt Ltd",      "city": "Pune",      "state": "Maharashtra", "lead_time_days": 21, "quality_score": 8.0, "supplier_tier": "PREFERRED"},
    {"supplier_id": "S003", "supplier_name": "ChemSource Gujarat",       "city": "Surat",     "state": "Gujarat",     "lead_time_days": 10, "quality_score": 7.5, "supplier_tier": "APPROVED"},
    {"supplier_id": "S004", "supplier_name": "NorthWest Plastics",       "city": "Ludhiana",  "state": "Punjab",      "lead_time_days": 18, "quality_score": 7.0, "supplier_tier": "APPROVED"},
    {"supplier_id": "S005", "supplier_name": "GreenField Polymers",      "city": "Chennai",   "state": "Tamil Nadu",  "lead_time_days": 25, "quality_score": 6.5, "supplier_tier": "BACKUP"},
    {"supplier_id": "S006", "supplier_name": "RapidMetal Solutions",     "city": "Jamshedpur","state": "Jharkhand",   "lead_time_days": 7,  "quality_score": 9.0, "supplier_tier": "APPROVED"},
    {"supplier_id": "S007", "supplier_name": "Eastern Chemical Works",   "city": "Kolkata",   "state": "West Bengal", "lead_time_days": 30, "quality_score": 5.5, "supplier_tier": "BACKUP"},
]

# ── 2. Materials ─────────────────────────────────────────────────────────────
MATERIALS = [
    {"material_id": "M001", "material_code": "HR-STEEL-COIL",   "material_name": "Hot-Rolled Steel Coil",        "category": "Metals",     "sub_category": "Ferrous",   "unit_of_measure": "MT"},
    {"material_id": "M002", "material_code": "HDPE-GRANULES",   "material_name": "HDPE Granules",                "category": "Plastics",   "sub_category": "Polyolefin","unit_of_measure": "kg"},
    {"material_id": "M003", "material_code": "COPPER-WIRE-ROD", "material_name": "Copper Wire Rod",              "category": "Metals",     "sub_category": "Non-Ferrous","unit_of_measure": "kg"},
    {"material_id": "M004", "material_code": "PALM-OIL-RBD",    "material_name": "Refined Bleached Palm Oil",   "category": "Chemicals",  "sub_category": "Oils",      "unit_of_measure": "kg"},
    {"material_id": "M005", "material_code": "ALUMINIUM-SHEET", "material_name": "Aluminium Sheet 2mm",         "category": "Metals",     "sub_category": "Non-Ferrous","unit_of_measure": "kg"},
    {"material_id": "M006", "material_code": "PP-COMPOUND",     "material_name": "Polypropylene Compound",      "category": "Plastics",   "sub_category": "Polyolefin","unit_of_measure": "kg"},
]

# ── 3. Material–Commodity Mappings ────────────────────────────────────────────
# exposure_weight per material sums to 1.0
COMMODITY_MAP = [
    {"map_id": "CM001", "material_id": "M001", "commodity_code": "LME_HRC_STEEL",  "commodity_name": "LME Hot-Rolled Coil Steel",  "exposure_weight": 0.85, "mapping_basis": "Steel coil spot price directly drives input cost",               "confidence": "HIGH"},
    {"map_id": "CM002", "material_id": "M001", "commodity_code": "COKING_COAL",    "commodity_name": "Coking Coal Index",           "exposure_weight": 0.15, "mapping_basis": "Coking coal is ~15% of steel production cost",                   "confidence": "MEDIUM"},
    {"map_id": "CM003", "material_id": "M002", "commodity_code": "NAPHTHA_SPOT",   "commodity_name": "Naphtha Spot Price",          "exposure_weight": 0.70, "mapping_basis": "HDPE is derived from naphtha feedstock via ethylene cracking",   "confidence": "HIGH"},
    {"map_id": "CM004", "material_id": "M002", "commodity_code": "BRENT_CRUDE",    "commodity_name": "Brent Crude Oil",             "exposure_weight": 0.30, "mapping_basis": "Crude oil is upstream feedstock for all petrochemicals",        "confidence": "MEDIUM"},
    {"map_id": "CM005", "material_id": "M003", "commodity_code": "LME_COPPER",     "commodity_name": "LME Copper Cash Price",       "exposure_weight": 0.92, "mapping_basis": "Copper wire rod price closely tracks LME copper spot",          "confidence": "HIGH"},
    {"map_id": "CM006", "material_id": "M003", "commodity_code": "BRENT_CRUDE",    "commodity_name": "Brent Crude Oil",             "exposure_weight": 0.08, "mapping_basis": "Energy cost component in copper smelting",                       "confidence": "LOW"},
    {"map_id": "CM007", "material_id": "M004", "commodity_code": "PALM_OIL_BMD",   "commodity_name": "Bursa Malaysia Palm Oil",    "exposure_weight": 0.90, "mapping_basis": "RBD palm oil is refined from crude palm oil (CPO)",             "confidence": "HIGH"},
    {"map_id": "CM008", "material_id": "M004", "commodity_code": "BRENT_CRUDE",    "commodity_name": "Brent Crude Oil",             "exposure_weight": 0.10, "mapping_basis": "Energy cost in refining process",                               "confidence": "LOW"},
    {"map_id": "CM009", "material_id": "M005", "commodity_code": "LME_ALUMINIUM",  "commodity_name": "LME Aluminium Cash Price",   "exposure_weight": 0.88, "mapping_basis": "Aluminium sheet price closely tracks LME aluminium",            "confidence": "HIGH"},
    {"map_id": "CM010", "material_id": "M005", "commodity_code": "BRENT_CRUDE",    "commodity_name": "Brent Crude Oil",             "exposure_weight": 0.12, "mapping_basis": "Energy-intensive smelting process",                             "confidence": "MEDIUM"},
    {"map_id": "CM011", "material_id": "M006", "commodity_code": "NAPHTHA_SPOT",   "commodity_name": "Naphtha Spot Price",          "exposure_weight": 0.75, "mapping_basis": "PP compound is a naphtha-derivative (propylene)",               "confidence": "HIGH"},
    {"map_id": "CM012", "material_id": "M006", "commodity_code": "BRENT_CRUDE",    "commodity_name": "Brent Crude Oil",             "exposure_weight": 0.25, "mapping_basis": "Crude oil upstream feedstock",                                  "confidence": "MEDIUM"},
]

# ── 4. Market signals (6 months + 1 month forecast / shock) ──────────────────
def _price_series(start_price: float, n: int, vol: float = 0.02) -> list[float]:
    """Geometric Brownian Motion price path, deterministic via SEED."""
    prices = [start_price]
    for _ in range(n - 1):
        drift = RNG.normal(0, vol)
        prices.append(round(prices[-1] * (1 + drift), 4))
    return prices

def generate_market_signals() -> pd.DataFrame:
    rows = []
    commodities = [
        ("LME_HRC_STEEL",  55000.0,  "INR/MT",  0.015),  # ~55k INR/MT
        ("COKING_COAL",    18500.0,  "INR/MT",  0.020),
        ("NAPHTHA_SPOT",   75.0,     "USD/bbl", 0.025),
        ("BRENT_CRUDE",    85.0,     "USD/bbl", 0.025),
        ("LME_COPPER",     8200.0,   "USD/MT",  0.018),
        ("PALM_OIL_BMD",   3900.0,   "MYR/MT",  0.022),
        ("LME_ALUMINIUM",  2350.0,   "USD/MT",  0.018),
    ]
    n_days = (END_DATE - START_DATE).days

    for code, start_price, unit, vol in commodities:
        prices = _price_series(start_price, n_days, vol)
        for i, price in enumerate(prices):
            rows.append({
                "signal_id": f"SIG-{code}-{i:04d}",
                "commodity_code": code,
                "signal_date": str(START_DATE + timedelta(days=i)),
                "price": round(price, 4),
                "currency": unit.split("/")[0],
                "unit": unit,
                "source": "SYNTHETIC",
                "is_synthetic": True,
            })
    return pd.DataFrame(rows)


# ── 5. Purchase lines (6 months, ~300 rows) ───────────────────────────────────
# M001 (Steel Coil) is deliberately sourced 90% from S001 — concentrated risk
PURCHASE_WEIGHT = {
    "M001": {"S001": 0.90, "S002": 0.10},
    "M002": {"S003": 0.55, "S004": 0.35, "S005": 0.10},
    "M003": {"S006": 0.65, "S001": 0.35},
    "M004": {"S003": 0.80, "S007": 0.20},
    "M005": {"S006": 0.50, "S002": 0.30, "S004": 0.20},
    "M006": {"S004": 0.60, "S005": 0.40},
}

# Base unit prices in INR for each material
BASE_UNIT_PRICE = {
    "M001": 52000.0,  # INR/MT
    "M002": 105.0,    # INR/kg
    "M003": 720.0,    # INR/kg
    "M004": 98.0,     # INR/kg
    "M005": 215.0,    # INR/kg
    "M006": 118.0,    # INR/kg
}

# Monthly purchase volumes (units)
MONTHLY_VOLUME = {
    "M001": 15.0,    # MT per month
    "M002": 5000.0,  # kg per month
    "M003": 2000.0,  # kg per month
    "M004": 8000.0,  # kg per month
    "M005": 3000.0,  # kg per month
    "M006": 6000.0,  # kg per month
}


def generate_purchase_lines() -> pd.DataFrame:
    rows = []
    current = START_DATE
    months = []
    while current < END_DATE:
        months.append(current)
        # advance to first of next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    po_seq = 1
    for month_start in months:
        for mat_id, supplier_weights in PURCHASE_WEIGHT.items():
            for sup_id, weight in supplier_weights.items():
                qty = round(MONTHLY_VOLUME[mat_id] * weight, 4)
                if qty <= 0:
                    continue
                price_noise = 1 + RNG.uniform(-0.03, 0.03)
                unit_price = round(BASE_UNIT_PRICE[mat_id] * price_noise, 4)
                total_value = round(qty * unit_price, 4)
                # purchase date = 5th of the month
                purchase_date = month_start.replace(day=5)
                rows.append({
                    "line_id": str(uuid.UUID(int=po_seq * 1000 + hash(mat_id + sup_id) % 1000)),
                    "po_number": f"PO-2025-{po_seq:05d}",
                    "purchase_date": str(purchase_date),
                    "material_id": mat_id,
                    "supplier_id": sup_id,
                    "quantity": qty,
                    "unit_price_inr": unit_price,
                    "total_value_inr": total_value,
                    "currency": "INR",
                    "inr_exchange_rate": 1.0,
                    "source": "SYNTHETIC",
                    "is_duplicate": False,
                })
                po_seq += 1
    return pd.DataFrame(rows)


# ── 6. Supplier quotations ────────────────────────────────────────────────────
def generate_quotations() -> pd.DataFrame:
    rows = [
        # M001 alternatives – S002 is feasible, S006 is feasible at lower price
        {"quote_id": "Q001", "supplier_id": "S001", "material_id": "M001", "quote_date": "2026-01-05", "unit_price_inr": 51800.0, "min_order_qty": 5.0,    "max_capacity_qty": 50.0,  "lead_time_days": 14, "quality_score": 8.5, "valid_until": "2027-06-30"},
        {"quote_id": "Q002", "supplier_id": "S002", "material_id": "M001", "quote_date": "2026-01-05", "unit_price_inr": 52500.0, "min_order_qty": 3.0,    "max_capacity_qty": 30.0,  "lead_time_days": 21, "quality_score": 8.0, "valid_until": "2027-06-30"},
        {"quote_id": "Q003", "supplier_id": "S006", "material_id": "M001", "quote_date": "2026-01-05", "unit_price_inr": 50900.0, "min_order_qty": 1.0,    "max_capacity_qty": 20.0,  "lead_time_days": 7,  "quality_score": 9.0, "valid_until": "2027-06-30"},
        # M002 – NorthWest Plastics is rejected (max capacity too low for required qty)
        {"quote_id": "Q004", "supplier_id": "S003", "material_id": "M002", "quote_date": "2026-01-05", "unit_price_inr": 103.0,   "min_order_qty": 500.0,  "max_capacity_qty": 8000.0,"lead_time_days": 10, "quality_score": 7.5, "valid_until": "2027-06-30"},
        {"quote_id": "Q005", "supplier_id": "S004", "material_id": "M002", "quote_date": "2026-01-05", "unit_price_inr": 101.0,   "min_order_qty": 1000.0, "max_capacity_qty": 1500.0,"lead_time_days": 18, "quality_score": 7.0, "valid_until": "2027-06-30"},  # REJECTED: capacity exceeded
        {"quote_id": "Q006", "supplier_id": "S005", "material_id": "M002", "quote_date": "2026-01-05", "unit_price_inr": 107.0,   "min_order_qty": 200.0,  "max_capacity_qty": 6000.0,"lead_time_days": 25, "quality_score": 6.5, "valid_until": "2027-06-30"},
        # M003 – S007 quality too low (VERIFY_FIRST case)
        {"quote_id": "Q007", "supplier_id": "S006", "material_id": "M003", "quote_date": "2026-01-05", "unit_price_inr": 715.0,   "min_order_qty": 500.0,  "max_capacity_qty": 5000.0,"lead_time_days": 7,  "quality_score": 9.0, "valid_until": "2027-06-30"},
        {"quote_id": "Q008", "supplier_id": "S007", "material_id": "M003", "quote_date": "2026-01-05", "unit_price_inr": 700.0,   "min_order_qty": 1000.0, "max_capacity_qty": 3000.0,"lead_time_days": 30, "quality_score": 5.5, "valid_until": "2027-06-30"},  # low quality = verify
        # M004 (Palm oil) – no alternative with known capacity → VERIFY_FIRST
        {"quote_id": "Q009", "supplier_id": "S003", "material_id": "M004", "quote_date": "2026-01-05", "unit_price_inr": 96.0,    "min_order_qty": 2000.0, "max_capacity_qty": None,  "lead_time_days": 10, "quality_score": 7.5, "valid_until": "2027-06-30"},
        # M005
        {"quote_id": "Q010", "supplier_id": "S006", "material_id": "M005", "quote_date": "2026-01-05", "unit_price_inr": 212.0,   "min_order_qty": 500.0,  "max_capacity_qty": 8000.0,"lead_time_days": 7,  "quality_score": 9.0, "valid_until": "2027-06-30"},
        {"quote_id": "Q011", "supplier_id": "S002", "material_id": "M005", "quote_date": "2026-01-05", "unit_price_inr": 218.0,   "min_order_qty": 300.0,  "max_capacity_qty": 5000.0,"lead_time_days": 21, "quality_score": 8.0, "valid_until": "2027-06-30"},
        # M006
        {"quote_id": "Q012", "supplier_id": "S004", "material_id": "M006", "quote_date": "2026-01-05", "unit_price_inr": 116.0,   "min_order_qty": 1000.0, "max_capacity_qty": 10000.0,"lead_time_days":18, "quality_score": 7.0, "valid_until": "2027-06-30"},
    ]
    return pd.DataFrame(rows)


# ── 7. Scenario runs (two shocks) ────────────────────────────────────────────
SCENARIO_RUNS = [
    {"scenario_id": "SC001", "scenario_name": "Brent Crude +15% Shock",         "commodity_code": "BRENT_CRUDE",   "shock_pct": 15.0, "shock_direction": "UP",   "analysis_period_start": "2025-07-01", "analysis_period_end": "2026-01-01", "created_by": "demo"},
    {"scenario_id": "SC002", "scenario_name": "LME Copper +20% Shock",           "commodity_code": "LME_COPPER",    "shock_pct": 20.0, "shock_direction": "UP",   "analysis_period_start": "2025-07-01", "analysis_period_end": "2026-01-01", "created_by": "demo"},
    {"scenario_id": "SC003", "scenario_name": "Naphtha -10% Improvement",         "commodity_code": "NAPHTHA_SPOT",  "shock_pct": 10.0, "shock_direction": "DOWN", "analysis_period_start": "2025-07-01", "analysis_period_end": "2026-01-01", "created_by": "demo"},
]


# ── 8. Expected analytical outputs (Python-calculated baseline) ───────────────
def compute_expected_outputs(
    purchase_df: pd.DataFrame,
    commodity_map_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Calculate expected outputs in Python for test comparison against Exasol.
    These are the canonical "gold" values.
    """
    expected: dict[str, Any] = {}

    # ── Total spend per material ──────────────────────────────────────────────
    spend_by_mat = (
        purchase_df.groupby("material_id")["total_value_inr"]
        .sum()
        .round(4)
        .to_dict()
    )
    expected["total_spend_by_material"] = spend_by_mat

    # ── Supplier HHI for M001 (expected: highly concentrated) ────────────────
    m001_purchases = purchase_df[purchase_df["material_id"] == "M001"]
    m001_total = m001_purchases["total_value_inr"].sum()
    m001_shares = m001_purchases.groupby("supplier_id")["total_value_inr"].sum() / m001_total * 100
    m001_hhi = round((m001_shares ** 2).sum(), 4)
    expected["m001_hhi"] = m001_hhi
    expected["m001_hhi_level"] = "HIGH" if m001_hhi > 2500 else "MEDIUM" if m001_hhi > 1500 else "LOW"
    expected["m001_dominant_supplier"] = m001_shares.idxmax()
    expected["m001_dominant_share_pct"] = round(m001_shares.max(), 4)

    # ── Scenario SC001: Brent Crude +15% ─────────────────────────────────────
    sc001 = scenario_df[scenario_df["scenario_id"] == "SC001"].iloc[0]
    brent_maps = commodity_map_df[commodity_map_df["commodity_code"] == "BRENT_CRUDE"]
    sc001_impacts = []
    for _, row in brent_maps.iterrows():
        obs_spend = spend_by_mat.get(row["material_id"], 0.0)
        exposed = round(obs_spend * row["exposure_weight"], 4)
        incremental = round(exposed * sc001["shock_pct"] / 100, 4)
        sc001_impacts.append({
            "material_id": row["material_id"],
            "observed_spend_inr": obs_spend,
            "exposed_spend_inr": exposed,
            "incremental_cost_inr": incremental,
        })
    expected["sc001_impacts"] = sc001_impacts
    expected["sc001_total_incremental"] = round(
        sum(r["incremental_cost_inr"] for r in sc001_impacts), 4
    )

    # ── Scenario SC002: LME Copper +20% ──────────────────────────────────────
    sc002 = scenario_df[scenario_df["scenario_id"] == "SC002"].iloc[0]
    copper_maps = commodity_map_df[commodity_map_df["commodity_code"] == "LME_COPPER"]
    sc002_impacts = []
    for _, row in copper_maps.iterrows():
        obs_spend = spend_by_mat.get(row["material_id"], 0.0)
        exposed = round(obs_spend * row["exposure_weight"], 4)
        incremental = round(exposed * sc002["shock_pct"] / 100, 4)
        sc002_impacts.append({
            "material_id": row["material_id"],
            "observed_spend_inr": obs_spend,
            "exposed_spend_inr": exposed,
            "incremental_cost_inr": incremental,
        })
    expected["sc002_impacts"] = sc002_impacts

    return expected


def main() -> None:
    print("Generating SupplyLens synthetic dataset (seed=42) …")

    # Build DataFrames
    suppliers_df = pd.DataFrame(SUPPLIERS)
    materials_df = pd.DataFrame(MATERIALS)
    commodity_map_df = pd.DataFrame(COMMODITY_MAP)
    market_signals_df = generate_market_signals()
    purchase_df = generate_purchase_lines()
    quotations_df = generate_quotations()
    scenario_df = pd.DataFrame(SCENARIO_RUNS)

    # Add ingestion_id placeholder
    purchase_df["ingestion_id"] = "SYNTHETIC-SEED-001"

    # Compute expected outputs for testing
    expected = compute_expected_outputs(purchase_df, commodity_map_df, scenario_df)

    # Write CSVs
    suppliers_df.to_csv(OUT_DIR / "suppliers.csv", index=False)
    materials_df.to_csv(OUT_DIR / "materials.csv", index=False)
    commodity_map_df.to_csv(OUT_DIR / "commodity_map.csv", index=False)
    market_signals_df.to_csv(OUT_DIR / "market_signals.csv", index=False)
    purchase_df.to_csv(OUT_DIR / "purchase_lines.csv", index=False)
    quotations_df.to_csv(OUT_DIR / "supplier_quotations.csv", index=False)
    scenario_df.to_csv(OUT_DIR / "scenario_runs.csv", index=False)

    # Write expected outputs as JSON (used by tests)
    with open(EXPECTED_DIR / "expected_outputs.json", "w") as f:
        json.dump(expected, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"  suppliers:        {len(suppliers_df)}")
    print(f"  materials:        {len(materials_df)}")
    print(f"  commodity maps:   {len(commodity_map_df)}")
    print(f"  market signals:   {len(market_signals_df)}")
    print(f"  purchase lines:   {len(purchase_df)}")
    print(f"  quotations:       {len(quotations_df)}")
    print(f"  scenarios:        {len(scenario_df)}")
    print()
    print("Expected analytical outputs:")
    print(f"  M001 HHI:              {expected['m001_hhi']:.1f} ({expected['m001_hhi_level']})")
    print(f"  M001 dominant supplier:{expected['m001_dominant_supplier']} @ {expected['m001_dominant_share_pct']:.1f}%")
    print(f"  SC001 total incremental cost (INR): {expected['sc001_total_incremental']:,.2f}")
    print()
    print(f"Files written to: {OUT_DIR}")
    print(f"Expected outputs: {EXPECTED_DIR / 'expected_outputs.json'}")


if __name__ == "__main__":
    main()
