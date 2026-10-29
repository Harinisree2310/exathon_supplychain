# SupplyLens — ExaThon India 2026 Submission Checklist

## Competition Requirements

### Core Product
- [x] Load labelled synthetic procurement dataset
- [x] Normalise purchase records and material descriptions
- [x] Map materials to commodity exposures with transparent rules
- [x] Load market observations and user-defined shocks
- [x] Use Exasol Personal for core analytical calculations
- [x] Calculate supplier concentration (HHI) and exposed spend
- [x] Evaluate supplier alternatives against hard constraints
- [x] Recommend defensible next action
- [x] Display evidence behind each result
- [x] Export report with assumptions, calculations and limitations
- [x] Record human approval/rejection

### Evidence Trace (Signature Feature)
- [x] Market signal → Material mapping → Purchase evidence → Exposure → Supplier comparison → Recommendation

### Exasol Integration
- [x] Official pyexasol Python connector (v3.0)
- [x] Version-controlled SQL schema (001_core_tables.sql)
- [x] Version-controlled views (001_analytical_views.sql)
- [x] Parameterised SQL queries (scenario_impact.sql, supplier_comparison.sql)
- [x] Schema initialisation (schema_init.py)
- [x] Seed data loader (seed_loader.py using import_from_pandas)
- [x] Connection health probe (probe_connection → HTTP 503 on failure)
- [ ] Live connection verified (BLOCKED: Exasol not reachable at localhost:8563 during audit)

### Data Requirements
- [x] At least 6 material types (6 created)
- [x] At least 5 suppliers (7 created)
- [x] 6 months of purchase history (Jul 2025 – Jan 2026, 84 lines)
- [x] At least 2 market signal series (7 commodities, 1,288 signals)
- [x] Multiple alternative supplier quotations (12 quotations)
- [x] Different MOQs and capacities
- [x] At least 1 concentrated dependency (M001, HHI 8,180)
- [x] At least 1 rejected alternative (Q005 — NorthWest Plastics, capacity exceeded)
- [x] At least 1 VERIFY_FIRST case (M003, M004 — low quality / unknown capacity)
- [x] Hypothetical shock scenarios (SC001: Brent +15%, SC002: Copper +20%, SC003: Naphtha -10%)

### Technical Stack
- [x] React + TypeScript + Vite + Tailwind CSS + Recharts
- [x] Python + FastAPI + Pydantic v2 + PyExasol + Pandas
- [x] Exasol Personal (schema + migrations + views + queries)

### User Interface (8 screens)
- [x] Overview — spend, concentration, quality warnings
- [x] Data Workspace — load demo, upload files, quality summary
- [x] Material Risk Explorer — history, signals, concentration
- [x] Scenario Lab — configure shock, compare baseline vs shocked
- [x] Supplier Comparison — hard constraint violations shown
- [x] Evidence Trace — inspect calculation provenance
- [x] Decision Review — approve/reject/defer with signature
- [x] Reports — export JSON/CSV

### API Endpoints
- [x] GET /health
- [x] GET /health/db
- [x] POST /api/v1/data/load-demo
- [x] GET /api/v1/data/quality
- [x] POST /api/v1/data/upload/purchases
- [x] GET /api/v1/data/template/purchases
- [x] GET /api/v1/analytics/materials
- [x] GET /api/v1/analytics/suppliers
- [x] GET /api/v1/analytics/market-signals
- [x] GET /api/v1/analytics/concentration
- [x] GET /api/v1/analytics/overview
- [x] GET /api/v1/analytics/spend-history
- [x] POST /api/v1/analytics/scenarios
- [x] GET /api/v1/analytics/scenarios
- [x] GET /api/v1/analytics/scenarios/{id}
- [x] POST /api/v1/analytics/scenarios/{id}/calculate
- [x] GET /api/v1/analytics/scenarios/{id}/results
- [x] GET /api/v1/analytics/supplier-comparison/{material_id}
- [x] POST /api/v1/analytics/recommendations
- [x] GET /api/v1/analytics/recommendations
- [x] GET /api/v1/analytics/evidence/{recommendation_id}
- [x] POST /api/v1/analytics/decisions
- [x] GET /api/v1/reports/export/{scenario_id}

### Safety and Correctness
- [x] No silent database fallback — HTTP 503 when Exasol unreachable
- [x] Savings never calculated from incompatible prices (NULL when unknown)
- [x] LLM never invents financial figures — deterministic fallback
- [x] Human review required on every recommendation
- [x] Synthetic data clearly labelled
- [x] Disclaimer in evidence traces and reports

### Tests
- [x] Exposure formula unit tests
- [x] HHI calculation correctness
- [x] Supplier feasibility logic
- [x] Recommendation engine (VERIFY_FIRST, zero-saving safety)
- [x] LLM fallback (deterministic, empty provider, invalid output)
- [x] Synthetic data generation (all files, row counts, coverage)
- [x] Data quality (weights sum to 1.0, no duplicate POs)
- [x] Ingestion logic (normalise, fingerprint)
- [x] API validation (scenario, decision, upload format)
- [ ] Live Exasol HHI comparison (BLOCKED: DB not connected)
- [ ] Live scenario incremental cost comparison (BLOCKED: DB not connected)

### Documentation
- [x] README with prerequisites and exact commands
- [x] .env.example
- [x] MIT licence
- [x] Architecture diagram (ARCHITECTURE.md)
- [x] Data dictionary (DATA_DICTIONARY.md)
- [x] Calculation methodology (METHODOLOGY.md)
- [x] Build status (BUILD_STATUS.md)
- [x] Pitch deck (PITCH_DECK.md)
- [x] Demo script and shot list (DEMO_SCRIPT.md)
- [x] Submission checklist (this file)

### Competition Deliverables
- [x] Complete source code
- [x] Exasol SQL scripts
- [x] Synthetic data and upload templates
- [x] Version-controlled repository structure

## Test Result Summary

```
49 passed | 3 skipped (BLOCKED: Exasol not reachable) | 0 failed (52 collected)
```

## Remaining Blocker

To complete the live Exasol acceptance test:

```powershell
irm https://www.exasol.com/install/starter-kit.ps1 | iex
cd backend
python -m app.db.seed_loader
python -m pytest tests/ -v
```

Expected result after Exasol is running: **51 passed, 0 skipped, 0 failed.**
