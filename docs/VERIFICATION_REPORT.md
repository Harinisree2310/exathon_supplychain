# SupplyLens Verification Report

**Run date:** 2026-10-28  
**Overall status:** **PASS** — live Exasol verification and the real browser workflow completed.  
**Submission assessment:** **Ready to submit for the demo**, provided Exasol Personal is running before launch.

## Database target and connectivity

The project is configured for **local Exasol Personal**, not a remote instance. The active application configuration uses `127.0.0.1:8563`; no remote host is configured. The runtime is Exasol Personal managed through Podman.

Credential values were not printed or recorded. `exakit info` reported:

```text
Runtime: personal
DSN:     127.0.0.1:8563
TLS:     enabled (self-signed certificate)
```

`exakit status` reported:

```text
Runtime  personal (podman) - running
Database 127.0.0.1:8563 - reachable
Autostart disabled
```

The status command also printed an unfinished-runtime retry notice despite reporting the runtime as running and the database reachable. No installer retry or repair was run because live authentication and application queries succeeded. Autostart is disabled; run `exakit start` before using the application if the database is stopped, including after a reboot.

Live application health response:

```text
GET http://127.0.0.1:8000/health
{"api":"ok","database":"connected","database_dsn":"127.0.0.1:8563","version":"1.0.0","environment":"development"}
```

**Connectivity, authentication and schema access: PASS.** The API opened the configured schema and returned Exasol-backed data.

## Initialization and loaded data

The seed loader initialized the project schema, base tables and analytical views and loaded the synthetic CSVs without resetting or truncating existing database data. It also refreshed the derived supplier-concentration table.

The live Data Workspace quality endpoint returned:

```json
{
  "total_materials": 6,
  "total_suppliers": 7,
  "total_purchase_lines": 84,
  "total_market_signals": 1288,
  "materials_with_mapping": 6,
  "materials_without_mapping": 0,
  "stale_signal_count": 7,
  "incomplete_quotations": 1,
  "data_source": "SYNTHETIC",
  "is_synthetic": true
}
```

Additional live checks reported 12 material/commodity mappings, 12 supplier quotations, 3 initial sample scenarios, and 14 derived supplier-concentration rows. Subsequent workflow verification added the UP-zero, DOWN-15%, and E2E scenarios. No orphan purchase lines were found. The quality endpoint reports 7 stale latest signals and 1 incomplete quotation; these are data-quality findings, not initialization failures.

## Live analytical verification

The following three database-dependent tests were explicitly run against the live database; none were skipped:

```powershell
Set-Location .\supplylens\backend
..\.venv\Scripts\python.exe -m pytest -q -rs `
  tests\test_analytics.py::TestLiveExasolAnalytics::test_hhi_matches_expected `
  tests\test_analytics.py::TestLiveExasolAnalytics::test_scenario_incremental_cost_matches_expected `
  tests\test_analytics.py::TestLiveExasolAnalytics::test_schema_initialised
```

Actual result:

```text
collected 3 items
tests\test_analytics.py ...                                              [100%]
3 passed in 7.30s
```

The live `M001` supplier HHI was `8179.9274000000005`, matching the independently calculated expected value `8179.9274`.

Signed-shock expected values were independently calculated from the raw synthetic purchase, mapping and scenario CSVs. The live scenario results endpoint returned 5 material rows in each case:

| Scenario | Direction | Independent expected total (INR) | Live Exasol total (INR) | Status |
|---|---:|---:|---:|---|
| SC001, Brent Crude +15% Shock | UP 15% | 544602.7054 | 544602.7054 | PASS |
| Live verification DOWN 15 | DOWN 15% | -544602.7054 | -544602.7054 | PASS |
| Live verification UP 0 | UP 0% | 0.0000 | 0 | PASS |

The live results were read with:

```powershell
$base = 'http://127.0.0.1:8000'
$scenarios = Invoke-RestMethod -Uri "$base/api/v1/analytics/scenarios"
foreach ($name in @('Brent Crude +15% Shock', 'Live verification DOWN 15', 'Live verification UP 0')) {
    $scenario = $scenarios | Where-Object { $_.scenario_name -eq $name } | Select-Object -First 1
    $rows = Invoke-RestMethod -Uri "$base/api/v1/analytics/scenarios/$($scenario.scenario_id)/results"
    $total = ($rows | Measure-Object -Property incremental_cost_inr -Sum).Sum
    "$name | direction=$($scenario.shock_direction) $($scenario.shock_pct)% | rows=$($rows.Count) | total=$total"
}
```

Observed totals:

```text
Brent Crude +15% Shock | direction=UP 15% | rows=5 | total=544602.7054
Live verification DOWN 15 | direction=DOWN 15% | rows=5 | total=-544602.7054
Live verification UP 0 | direction=UP 0% | rows=5 | total=0
```

The up/down totals are equal and opposite; zero shock yields exactly zero incremental cost.

## Real API and frontend workflow

The API and Vite frontend were started locally and exercised in the browser. After the API restart required to apply the supplier fixes, the UI showed **Exasol connected** during the completed flow. A transient proxy connection refusal occurred while the backend was restarting.

1. **Scenario creation and calculation:** Created `SupplyLens E2E Verification 2026-10-28` for Brent Crude, UP 15%, period `2025-07-01` to `2026-01-01`. The scenario ID is `ffb8fd92-af1b-4ee8-8768-91d36923e827`. The browser reported **“Calculated: 5 material exposures”** and displayed a total incremental cost of ₹5.45 L. The live total was INR `544602.7054`.
2. **Supplier comparison:** Compared Copper Wire Rod (`M003`) at quantity 1,000, max lead time 30 days, and minimum quality 6. The UI showed RapidMetal Solutions as the single feasible alternative at INR 715/unit, MOQ 500, capacity 5,000, 7 days, quality 9.0. Eastern Chemical Works at INR 700/unit was explicitly rejected for `QUALITY BELOW THRESHOLD`.
3. **Recommendation:** Generated and reviewed a `SWITCH_SUPPLIER` recommendation for `M003`, recommending RapidMetal Solutions (`S006`). The displayed indicative saving was INR `2073.90`; the recommendation required human review.
4. **Human decision:** Recorded `APPROVED` by `SupplyLens Verification` with the note “Approved after live supplier comparison and human review.”
5. **JSON report export:** Clicked **Export JSON Report** in the Reports page; the UI displayed **“Report downloaded as JSON.”** The corresponding live endpoint returned HTTP 200, `application/json`, 4,495 bytes. The JSON contained the scenario, 5 exposure results totaling INR `544602.7054`, 1 recommendation, and 1 decision. The decision ID was `5d531775-b312-4e87-bfe1-9a2ef8cd65ef`.

The export was independently checked with:

```powershell
$id = 'ffb8fd92-af1b-4ee8-8768-91d36923e827'
$response = Invoke-WebRequest -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/api/v1/reports/export/$id`?fmt=json"
$report = $response.Content | ConvertFrom-Json
```

Observed output:

```text
HTTP 200; content_type=application/json; bytes=4495
scenario=SupplyLens E2E Verification 2026-10-28; exposure_rows=5; total_incremental=544602.7054
recommendations=1; decisions=1
recommendation material=M003; action=SWITCH_SUPPLIER; alternative=S006; saving=2073.9; human_review=True
decision=APPROVED; decided_by=SupplyLens Verification
```

## Defects found and fixed

- Corrected `V_LATEST_MARKET_SIGNAL` to join against the subquery's `latest_date` alias.
- Kept PyExasol's bulk import encrypted and scoped `IGNORE CERTIFICATE` to its temporary HTTPS import; specified DataFrame import columns to match the supplied tables.
- Removed a `{param}` token from a SQL comment because PyExasol treated it as a bind placeholder.
- Fixed the live supplier list query: `state` is reserved by Exasol and could not be used as an unquoted SQL alias.
- Serialized supplier quote decimal values as JSON numbers. The browser expects numeric `quality_score`; before the fix, Pydantic emitted a string and the supplier-comparison page threw `toFixed is not a function`.

The reserved-word query and JSON numeric contract have focused regression tests.

## Test and build results

Full backend suite:

```powershell
Set-Location .\supplylens\backend
..\.venv\Scripts\python.exe -m pytest -q
```

Actual result:

```text
collected 57 items
tests\test_analytics.py .....................                            [ 36%]
tests\test_api.py .................                                      [ 66%]
tests\test_connection.py ...                                             [ 71%]
tests\test_data_generation.py ................                           [100%]
57 passed, 1 warning in 9.46s
```

There were **0 skipped and 0 failed** tests. The warning is Starlette's existing `BlockingPortal` deprecation notice.

Frontend production build:

```powershell
Set-Location .\supplylens\frontend
npm run build
```

Actual result: `tsc` passed; Vite transformed 2,430 modules and built successfully. The main JavaScript bundle is 774.80 kB before gzip (226.30 kB gzip); Vite emitted its existing non-fatal warning that chunks exceed 500 kB.

## Safety and readiness

No database reset, truncation, or destructive repair was run. Verification added one scenario, its calculated exposures, one recommendation, and one decision using synthetic data.

**Exasol verified end to end: YES. Application ready to submit: YES, for the current local demo configuration.** Exasol Personal is currently reachable at `127.0.0.1:8563`; because autostart is disabled, verify it is running before a demo with `exakit status`, and start it with `exakit start` if needed. No live verification claim depends on a mocked database or a skipped test.
