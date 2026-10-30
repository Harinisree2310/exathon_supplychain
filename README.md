# SupplyLens — Shock-to-Decision Intelligence for Indian SMBs

> **ExaThon India 2026** | Open-source supply-chain analytics MVP powered by **Exasol Personal**

SupplyLens helps small and medium-sized manufacturers understand how changes in commodity prices or foreign-exchange rates affect their purchased materials and procurement costs — with every figure traceable back to its source data.

---

## Quick Start (5 minutes)

### Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10/11 (8 GB+ RAM, 20 GB free disk) | Exasol Personal requires Podman |
| Python 3.11+ | `python --version` |
| Node.js 18+ | `node --version` |
| Podman Desktop (recommended) | From https://podman-desktop.io |

### Step 1 — Install Exasol Personal

```powershell
irm https://www.exasol.com/install/starter-kit.ps1 | iex
```

This installs Exasol Personal, pyexasol, exapump and the MCP server.
Exasol listens on **localhost:8563** (default credentials: `sys` / `exasol`).

### Step 2 — Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env if your Exasol password differs from 'exasol'
```

### Step 3 — Backend setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python data/synthetic/generate_dataset.py
cd backend
python -m app.db.seed_loader          # initialise schema + load demo data
uvicorn app.main:app --reload          # start API on http://localhost:8000
```

### Step 4 — Frontend setup

```powershell
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

### Step 5 — Run tests

```powershell
cd backend
python -m pytest tests/ -v
```

Expected results without Exasol: **49 passed, 3 skipped** (live DB tests marked BLOCKED; the current suite collects 52 tests).
With Exasol running: all 44 tests should pass.

---

## Architecture

```
Browser (React + Vite)
        │  HTTP REST
        ▼
FastAPI (Python)
        │  pyexasol WebSocket
        ▼
Exasol Personal (localhost:8563)
        │  Analytical SQL
        ▼
SUPPLYLENS schema (12 tables, 6 views, SQL queries)
```

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, TanStack Query
- **Backend:** FastAPI 0.111, Pydantic v2, PyExasol 3.0
- **Database:** Exasol Personal (all aggregations, HHI, exposure calcs, supplier comparison)
- **LLM:** Optional — deterministic fallback always available

### Frontend branding

The responsive app shell and shared component styles are in `frontend/src/index.css`.
To rebrand a deployment, update the CSS custom properties in `:root` (brand,
canvas, surface and sidebar colors); the navigation and page content remain
unchanged. The frontend works on desktop and mobile without a separate theme
dependency.

---

## Exasol Integration

All analytical work happens in Exasol:

| Query | File |
|---|---|
| Material spend summary | `V_MATERIAL_SPEND` view |
| Supplier HHI | `V_MATERIAL_HHI` view |
| Material exposure | `V_MATERIAL_EXPOSURE` view |
| Scenario impact | `database/queries/scenario_impact.sql` |
| Supplier comparison | `database/queries/supplier_comparison.sql` |
| Latest market signals | `V_LATEST_MARKET_SIGNAL` view |

The application **never** silently falls back to in-memory calculations. If Exasol is unreachable, the API returns HTTP 503 and the frontend displays an actionable error.

**Local demo only:** the sample configuration defaults to Exasol's `sys` account and
the starter-kit password, and the API has no authentication or authorization. Do
not expose this API or its database port to an untrusted network. For any shared
deployment, configure a dedicated least-privilege Exasol user, replace all
development credentials, and add an authentication layer first.

---

## Key Formulas

| Metric | Formula |
|---|---|
| Exposed spend | `observed_spend × exposure_weight` |
| Incremental cost | `exposed_spend × (shock_pct / 100)` |
| HHI | `SUM( (supplier_share_pct)² )` per material |
| Feasibility | price known AND qty ≥ MOQ AND qty ≤ capacity AND lead_time ≤ max AND quality ≥ min |
| Estimated saving | `(current_avg_price − alternative_price) × historical_volume` — only when both prices are known |

---

## Project Structure

```
supplylens/
├── frontend/              React + TypeScript + Vite frontend
├── backend/
│   ├── app/
│   │   ├── api/v1/        FastAPI route handlers
│   │   ├── core/          Configuration, logging
│   │   ├── db/            Exasol connection, schema init, seed loader
│   │   ├── schemas/       Pydantic response schemas
│   │   └── services/      Analytics, ingestion, evidence, LLM
│   └── tests/             Unit + integration tests
├── database/
│   ├── schema/            DDL (CREATE TABLE IF NOT EXISTS)
│   ├── views/             Analytical views
│   ├── queries/           Parameterised SQL queries
│   └── seed/              (populated by generate_dataset.py)
├── data/
│   ├── synthetic/         Generated CSVs (seed=42, deterministic)
│   └── expected/          Python-computed gold values for test comparison
├── scripts/               Setup and test scripts
├── docs/                  Architecture, data dictionary, methodology
└── pitch/                 Pitch deck and demo script
```

---

## Demo Workflow

1. **Load demo data** — Data Workspace → "Load Demo Data"
2. **Check concentration** — Overview dashboard shows M001 (Steel Coil) HHI = 8180 (HIGH)
3. **Create scenario** — Scenario Lab → Brent Crude +15% UP
4. **Run calculation** — Click "Run Calculation" → Exasol returns exposure results
5. **Compare suppliers** — Supplier Comparison → M002 (HDPE) → NorthWest Plastics rejected (capacity)
6. **Generate recommendation** — Decision Review → Generate for SC001 / M001
7. **Inspect evidence** — Evidence Trace shows full chain from market signal to recommendation
8. **Export report** — Reports → Export JSON
9. **Record decision** — Decision Review → Approve / Reject / Defer

---

## Limitations and Disclaimers

- All supplier and market data is **synthetic**. No real businesses or market prices.
- Exposure weights are documented assumptions, not audited financial analysis.
- Incremental cost estimates assume linear price pass-through.
- Saving estimates are indicative only; actual savings depend on negotiated terms.
- This tool does not place orders or initiate procurement actions.
- Not a substitute for professional procurement advice.

---

## Licence

MIT — see `LICENSE`

## Competition

ExaThon India 2026 | Genuine Exasol analytics | Open-source
