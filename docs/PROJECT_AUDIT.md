# SupplyLens Project Audit

**Audit date:** 2026-10-27  
**Project:** SupplyLens — Shock-to-Decision Intelligence for Indian SMBs  
**Scope:** Source, configuration, SQL, generated demo data, tests, documentation, and UI/API contracts.  
**Important limitation:** Exasol was not reachable at `localhost:8563`; live SQL, schema initialization, bulk import, and the complete database-backed demo could not be verified. No values were read from the local `.env`.

## Executive summary

SupplyLens is an existing React/Vite frontend with a FastAPI backend and an Exasol-oriented schema, query, and seed layer. The synthetic dataset is present and reproducible. Its analytical SQL is intended to execute in Exasol; Python handles orchestration and deterministic recommendation rules.

The backend suite passes locally, and the frontend production build succeeds. These results do **not** establish that the database-backed workflow works: all three live-Exasol tests are skipped, and the database port was unreachable during this audit. The application should be presented as a local MVP whose live Exasol acceptance remains blocked, not as an end-to-end verified deployment.

Several concrete defects and misleading claims were found. The audit fixes below correct the recommendation quantity passed to the decision engine, price-weighting for saving estimates, missing-evidence HTTP status, unbounded upload read, expired synthetic supplier quotations, and materially incorrect documentation. Remaining security, migration, evidence-provenance, and live-integration gaps are recorded explicitly.

## 1. Current architecture

```text
React 18 / TypeScript / Vite browser
        │ REST (Vite proxy in development)
        ▼
FastAPI / Pydantic backend
        │ pyexasol WebSocket
        ▼
Exasol Personal, SUPPLYLENS schema
```

- **Frontend:** `frontend/src/App.tsx` routes eight pages: Overview, Data Workspace, Material Risk, Scenario Lab, Supplier Comparison, Evidence Trace, Decision Review, and Reports.
- **Backend:** `backend/app/main.py` mounts health, data, analytics, and report routes. `backend/app/services/` contains SQL orchestration, CSV/Excel ingestion, evidence assembly, and an optional LLM explainer.
- **Database:** `database/schema/001_core_tables.sql` defines 12 tables; `database/views/001_analytical_views.sql` defines 6 views. `database/queries/` contains the scenario-impact and supplier-comparison SQL. The seed loader initializes the schema and loads CSV data with `pyexasol.import_from_pandas`.
- **Configuration:** `.env.example` documents Exasol, API, upload, CORS, and optional LLM settings. `.env` is ignored by `.gitignore`; it was deliberately not read.
- **Data:** `data/synthetic/` contains the deterministic generator and CSV inputs; `data/expected/expected_outputs.json` contains Python-side expected values for live database comparison.
- **Tests and scripts:** tests live under `backend/tests/`; setup, seed, connection-check, and test-runner scripts live under `scripts/`.
- **Documentation and pitch:** README, architecture, methodology, data dictionary, build status, checklist, demo script, and pitch deck are present.
- **Deployment:** no Docker/Compose manifest or CI workflow was found. The frontend has a development proxy; the README describes local execution.

## 2. Implemented behavior verified from source

1. **Synthetic data:** seed-42 generator produces 7 suppliers, 6 materials, 12 commodity mappings, 1,288 market observations, 84 purchase lines, 12 quotations, and 3 scenarios. Quote validity is now checked against the current date by a test.
2. **Schema/seed path:** schema initialization creates tables and views, verifies a subset of schema objects, and loads the synthetic CSVs. The seed loader remaps CSV source/state fields to DDL column names.
3. **Analytics:** Exasol SQL calculates monthly spend, supplier share/HHI, scenario exposure/cost, latest market signals, and quotation feasibility/ranks.
4. **API:** health, data loading/quality/upload/template, material/supplier/signal/concentration, scenario calculation/results, recommendation, evidence, decision, overview/spend history, and JSON/CSV report routes are present.
5. **Human review:** decisions are recorded as `DECISION_EVENTS`; recommendation rows require human review.
6. **Fallback behavior:** the LLM explanation service has deterministic templates. No in-memory analytics fallback was found in the calculation path.

These are source-level findings, not claims that Exasol-backed paths passed at runtime.

## 3. Incomplete or unverified features

- **Live Exasol workflow:** connectivity, DDL compatibility, Exasol SQL dialect/runtime behavior, import, persistence, and report queries remain unverified in this environment.
- **Market-signal-to-shock link:** the user enters a hypothetical shock percentage. Market history is shown as context/evidence; the scenario query applies the entered percentage and does not derive it from a signal price movement.
- **Evidence reproducibility:** evidence rebuilding re-runs supplier alternatives using historical quantity and default lead-time/quality thresholds. The original recommendation’s requested quantity and custom thresholds are not stored with the recommendation, so evidence may not reproduce the exact decision inputs.
- **Schema migration:** `CREATE TABLE IF NOT EXISTS` does not evolve an existing table. Compatibility checks require columns on only four tables, not every queried table. An old/partial schema can pass this check and fail later during a request.
- **LLM integration:** `explain_recommendation` exists and has unit tests, but it is not called by the recommendation API or rendered by the frontend. The optional LLM is not an end-to-end feature.
- **Decision queue:** the Decision Review page labels its list “Pending Recommendations,” but the list endpoint returns recommendations without filtering those already decided. Decision history is append-only, and no current decision status is joined into that list.
- **Frontend automated tests:** no frontend test script or frontend test files are present. `npm run build` type-checks and bundles the app but does not exercise browser workflows.
- **Deployment hardening:** no authentication/authorization layer, production serving configuration, container manifest, or CI pipeline was found.
- **Git baseline:** the project directory is not a Git repository, so branch state and tracked/untracked changes could not be established.

## 4. Confirmed defects and remediation

| Status | Finding | Source |
|---|---|---|
| Fixed | The recommendation endpoint checked supplier feasibility using request `required_qty` but failed to pass that quantity into the recommendation engine. Saving and split-allocation calculations could therefore use a different quantity. The route now forwards the same quantity. | [`backend/app/api/v1/analytics.py:261`](../backend/app/api/v1/analytics.py#L261); engine parameter [`backend/app/services/analytics.py:327`](../backend/app/services/analytics.py#L327) |
| Fixed | The incumbent unit price used an unweighted `AVG(unit_price_inr)`, which can misstate the historical price when purchase-line quantities differ. It now calculates `SUM(total_value_inr) / SUM(quantity)` for non-duplicate lines. | [`backend/app/services/analytics.py:408`](../backend/app/services/analytics.py#L408) |
| Fixed | An unknown recommendation produced a successful HTTP response containing an `error` object, not a not-found response. The route now returns HTTP 404. | [`backend/app/services/evidence.py:37`](../backend/app/services/evidence.py#L37); [`backend/app/api/v1/analytics.py:309`](../backend/app/api/v1/analytics.py#L309) |
| Fixed | Upload size was checked only after reading the entire upload into memory, defeating the intended application-level size cap. The endpoint now reads at most `MAX_UPLOAD_BYTES + 1` before rejecting an oversized file. | [`backend/app/api/v1/data.py:71`](../backend/app/api/v1/data.py#L71) |
| Fixed | All 12 synthetic quotations expired on 2026-06-30. At the audit date the feasibility query would reject every offer as expired before checking MOQ/capacity, defeating the supplier-comparison demo. Quote validity is now 2027-06-30 and a test fails when all demo quotes become stale. | [`data/synthetic/generate_dataset.py:197`](../data/synthetic/generate_dataset.py#L197); [`backend/tests/test_data_generation.py:91`](../backend/tests/test_data_generation.py#L91) |
| Fixed | `.xls` uploads were advertised and passed to `pandas.read_excel`, but `xlrd` was not in the backend requirements, so legacy `.xls` files could not be decoded in a clean environment. `xlrd==2.0.1` is now declared and installed in the working environment. | [`backend/app/api/v1/data.py:62`](../backend/app/api/v1/data.py#L62); [`backend/requirements.txt:8`](../backend/requirements.txt#L8) |
| Fixed | The convenience seed launcher hard-coded the original developer's absolute workspace path, so it failed from another checkout location. It now resolves the project relative to the batch file. | [`scripts/run.bat:2`](../scripts/run.bat#L2) |
| Fixed | The live-test preflight used process environment variables rather than the app's Pydantic settings, so a custom endpoint in `.env` could be probed incorrectly and its database tests skipped. It now uses `get_settings()`; a test asserts the configured host and port are used. | [`backend/tests/conftest.py:45`](../backend/tests/conftest.py#L45); [`backend/tests/test_data_generation.py:96`](../backend/tests/test_data_generation.py#L96) |
| Fixed | Data quality measured “stale” observations relative to the newest date in the same historical dataset, so it did not report whether each commodity’s latest signal was stale today. It now counts commodities whose latest signal is over 30 days behind `CURRENT_DATE`. | [`backend/app/services/analytics.py:63`](../backend/app/services/analytics.py#L63); [`backend/app/schemas/common.py`](../backend/app/schemas/common.py) |
| Fixed | CSV exports contained scenario metadata and exposure results only, despite the UI implying the exported reports included recommendations and decisions. The UI now states CSV's limited scope; JSON exports include recommendation evidence summaries, savings basis, selected supplier, and recorded decision notes. | [`backend/app/api/v1/reports.py`](../backend/app/api/v1/reports.py); [`backend/tests/test_api.py:228`](../backend/tests/test_api.py#L228); [`frontend/src/pages/Reports.tsx:46`](../frontend/src/pages/Reports.tsx#L46) |
| Fixed | Documentation stated 10 tables/5 views, but DDL and schema initialization contain 12 tables/6 views. Architecture/build docs were corrected. | [`backend/app/db/schema_init.py:28`](../backend/app/db/schema_init.py#L28); [`database/schema/001_core_tables.sql:5`](../database/schema/001_core_tables.sql#L5); [`database/views/001_analytical_views.sql:8`](../database/views/001_analytical_views.sql#L8) |
| Fixed | Methodology documentation said a quotation with unknown capacity could be feasible, contradicting SQL which returns `CAPACITY_UNKNOWN`. Documentation now matches the fail-closed query behavior. | [`database/queries/supplier_comparison.sql`](../database/queries/supplier_comparison.sql); [`docs/METHODOLOGY.md`](./METHODOLOGY.md) |
| Fixed | The demo script claimed data was “computed in-memory,” and the pitch deck claimed automatic market-price mapping, benchmarked sub-second performance, unsupported test/DDL counts, and ₹78 lakh spend. The verified Python reference totals ₹2.92 crore; the pitch now labels it as a reference and marks live Exasol verification pending. | [`pitch/DEMO_SCRIPT.md:30`](../pitch/DEMO_SCRIPT.md#L30); [`pitch/PITCH_DECK.md:91`](../pitch/PITCH_DECK.md#L91); expected values [`data/expected/expected_outputs.json`](../data/expected/expected_outputs.json) |
| Open | Schema verification checks required columns for only `SUPPLIERS`, `MARKET_SIGNALS`, `PURCHASE_LINES`, and `INGESTION_RECORDS`; other existing tables are not checked for query-required columns. | [`backend/app/db/schema_init.py:53`](../backend/app/db/schema_init.py#L53); [`backend/app/db/schema_init.py:214`](../backend/app/db/schema_init.py#L214) |
| Open | Evidence reconstruction uses historical quantity and default thresholds rather than the original recommendation inputs; those inputs are not persisted. | [`backend/app/services/evidence.py:180`](../backend/app/services/evidence.py#L180); [`backend/app/services/evidence.py:181`](../backend/app/services/evidence.py#L181); recommendation query inputs [`backend/app/api/v1/analytics.py:240`](../backend/app/api/v1/analytics.py#L240) |

## 5. Database schema and query inventory

### Tables (12)

`SUPPLIERS`, `MATERIALS`, `PURCHASE_LINES`, `MATERIAL_COMMODITY_MAP`, `MARKET_SIGNALS`, `SUPPLIER_QUOTATIONS`, `SCENARIO_RUNS`, `EXPOSURE_RESULTS`, `SUPPLIER_CONCENTRATION`, `RECOMMENDATIONS`, `DECISION_EVENTS`, `INGESTION_RECORDS`.

### Views (6)

`V_MATERIAL_SPEND`, `V_SUPPLIER_SHARE`, `V_MATERIAL_HHI`, `V_MATERIAL_EXPOSURE`, `V_LATEST_MARKET_SIGNAL`, `V_SUPPLIER_QUOTE_COMPARISON`.

### SQL query files (2)

- `database/queries/scenario_impact.sql`: scenario-period spend, commodity mapping weight, direction-signed incremental cost, and line/supplier counts.
- `database/queries/supplier_comparison.sql`: quote validity, price, MOQ, capacity, lead-time, and quality checks plus price rank.

### Naming/schema notes

- CSV `state`/`source` headings are remapped to `supplier_state`, `signal_source`, and `purchase_source` by the seed loader.
- DDL does not enforce a unique material code, despite older data-dictionary language implying uniqueness.
- `PURCHASE_LINES.ingestion_id` is not declared as a foreign key in the DDL.
- Current seed data and “expected” outputs are synthetic; market observations are generated, not a live feed.
- The data dictionary has been corrected for these and other column-name/type/status mismatches.

## 6. API and frontend integration

### Routes present

- `GET /`, `GET /health`, `GET /health/db`
- `POST /api/v1/data/load-demo`, `GET /api/v1/data/quality`, `POST /api/v1/data/upload/purchases`, `GET /api/v1/data/template/purchases`
- `GET /api/v1/analytics/materials`, `/suppliers`, `/market-signals`, `/concentration`, `/overview`, `/spend-history`
- `POST /api/v1/analytics/scenarios`, `GET /api/v1/analytics/scenarios`, `GET /api/v1/analytics/scenarios/{scenario_id}`
- `POST /api/v1/analytics/scenarios/{scenario_id}/calculate`, `GET /api/v1/analytics/scenarios/{scenario_id}/results`
- `GET /api/v1/analytics/supplier-comparison/{material_id}`
- `POST /api/v1/analytics/recommendations`, `GET /api/v1/analytics/recommendations`
- `GET /api/v1/analytics/evidence/{recommendation_id}`, `POST /api/v1/analytics/decisions`
- `GET /api/v1/reports/export/{scenario_id}` (JSON by default, CSV when requested)

The frontend API client uses the matching paths for its main flows. The audit fixes add coverage for recommendation quantity forwarding and missing evidence handling. Remaining limitation: evidence rebuild inputs are not persisted, as described above. No live browser-to-API-to-Exasol run was possible.

## 7. Tests and actual status

- Backend: **52 collected; 49 passed, 3 skipped, 0 failed** after the audit fixes.
- Test files: `backend/tests/test_analytics.py`, `backend/tests/test_api.py`, and `backend/tests/test_data_generation.py`, configured by `backend/tests/conftest.py`.
- The three skips are marked `requires_db`; the fixture performs a TCP reachability check and skips if Exasol is unavailable.
- The live tests cover an HHI comparison, a scenario incremental-cost comparison, and basic seeded table counts. They did not execute in this environment.
- Non-DB tests include formula/HHI examples, synthetic dataset checks, recommendation service behavior, LLM fallback behavior, and mocked API validation.
- Several formula tests are Python-side tests or mocked-query tests; they are not substitutes for validating the SQL in Exasol.
- Frontend: `npm run build` passes (TypeScript plus Vite production build); Vite warns that the main minified JS chunk exceeds 500 kB. No frontend test runner is defined.
- `docs/test_results.txt` is a test-output snapshot; the audit run above is the current authoritative result.

## 8. Exasol connectivity and execution

- TCP check to `localhost:8563`: **unreachable** at audit time.
- Database credentials were not tested, and the database was not contacted.
- The test suite’s three live checks therefore remained skipped.
- Accordingly, Exasol DDL acceptance, analytical query results, seed import, scenario/recommendation persistence, evidence retrieval, and export remain **not verified**.
- The Python-generated expected values (including M001 HHI `8179.9274` and SC001 incremental cost `544602.7054`) are reference data only until compared against a live Exasol result.

## 9. Security and deployment observations

- The configuration defaults to Exasol user `sys` and starter-kit password `exasol`; the README now clearly labels this as local-demo-only. Use a dedicated least-privilege database user for any shared deployment. See [`backend/app/core/config.py:25`](../backend/app/core/config.py#L25).
- The API exposes mutating data/scenario/recommendation/decision routes without application authentication or authorization. `SECRET_KEY` is configured but no authentication middleware or token validation is wired into the routes.
- CORS origins are configurable, but allowed methods and headers are wildcarded. This does not provide API authorization. See [`backend/app/main.py:44`](../backend/app/main.py#L44).
- The configuration default for backend host is `0.0.0.0`; keep the service on loopback or behind an authenticated, appropriately configured reverse proxy. See [`backend/app/core/config.py:30`](../backend/app/core/config.py#L30).
- `.env` is excluded by `.gitignore`, but because this workspace has no Git metadata, whether any local file is tracked cannot be verified. No environment secret was read, copied, or included in this report.
- No production deployment manifest, CI pipeline, or authentication configuration was found.

## 10. Reproducible validation

From the project root:

```powershell
python data/synthetic/generate_dataset.py
cd backend
python -m pytest -q
cd ..\frontend
npm run build
```

To complete live validation, start Exasol Personal, configure a dedicated local demo account in an ignored `.env`, initialize/seed using `python -m app.db.seed_loader` from `backend`, then rerun the backend suite and exercise the UI workflow. Do not treat skipped tests as passed database tests.

## 11. Workspace findings

- The actual project is the `supplylens` subdirectory of the opened workspace.
- `git status` and `git rev-parse` fail there because it is not a Git repository.
- `backend/`, `frontend/`, `database/{schema,views,queries}/`, `data/{synthetic,expected}/`, `scripts/`, `docs/`, and `pitch/` are present.
- `backend/tests/` contains the test suite. A root `tests/` directory exists but contains no files.
- Generated dependencies, virtual environments, caches, and the local `.env` were excluded from source review.
