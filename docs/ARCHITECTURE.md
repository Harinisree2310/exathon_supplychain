# SupplyLens Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  React 18 · TypeScript · Vite · Tailwind · Recharts     │
│  TanStack Query (data fetching) · react-router-dom      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP REST  (proxy: localhost:5173 → 8000)
┌────────────────────────▼────────────────────────────────┐
│  FastAPI (Python 3.11)                                  │
│  ├── /health              health + DB probe             │
│  ├── /api/v1/data         ingestion + quality           │
│  ├── /api/v1/analytics    materials, scenarios,          │
│  │                        concentration, exposure,      │
│  │                        suppliers, recommendations,   │
│  │                        evidence, decisions, overview  │
│  └── /api/v1/reports      JSON/CSV export               │
│                                                         │
│  Services:                                              │
│  ├── analytics.py         Exasol queries → Pydantic     │
│  ├── ingestion.py         CSV/Excel → Exasol INSERT     │
│  ├── evidence.py          Evidence chain builder        │
│  └── llm_explainer.py     Optional LLM / fallback       │
└────────────────────────┬────────────────────────────────┘
                         │ pyexasol WebSocket (port 8563)
┌────────────────────────▼────────────────────────────────┐
│  Exasol Personal (Podman container)                     │
│  Schema: SUPPLYLENS                                     │
│  ├── Tables (12): SUPPLIERS, MATERIALS, PURCHASE_LINES, │
│  │                MATERIAL_COMMODITY_MAP, MARKET_SIGNALS,│
│  │                SUPPLIER_QUOTATIONS, SCENARIO_RUNS,   │
│  │                EXPOSURE_RESULTS, SUPPLIER_CONCENTRATION,│
│  │                RECOMMENDATIONS, DECISION_EVENTS,     │
│  │                INGESTION_RECORDS                     │
│  ├── Views (6):   V_MATERIAL_SPEND, V_SUPPLIER_SHARE,   │
│  │                V_MATERIAL_HHI, V_MATERIAL_EXPOSURE,  │
│  │                V_LATEST_MARKET_SIGNAL,               │
│  │                V_SUPPLIER_QUOTE_COMPARISON           │
│  └── Queries:     scenario_impact.sql                   │
│                   supplier_comparison.sql               │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. SEED DATA
   generate_dataset.py (seed=42)
        │
        ▼ CSV files
   seed_loader.py
        │ pyexasol.import_from_pandas
        ▼
   Exasol tables

2. SCENARIO ANALYSIS
   User → POST /api/v1/analytics/scenarios
        │
        ▼ INSERT SCENARIO_RUNS
   Exasol
        │
   POST /api/v1/analytics/scenarios/{id}/calculate
        │ executes scenario_impact.sql
        ▼
   Exasol → EXPOSURE_RESULTS (persisted)
        │
        ▼
   POST /api/v1/analytics/recommendations
        │ deterministic engine
        ▼
   Exasol → RECOMMENDATIONS (persisted)

3. EVIDENCE TRACE
   GET /api/v1/analytics/evidence/{rec_id}
        │ 6 Exasol queries
        ▼
   Evidence chain JSON → Frontend

4. DECISION
   POST /api/v1/analytics/decisions
        │
        ▼
   Exasol → DECISION_EVENTS (persisted)
```

## Security Decisions

- No arbitrary SQL execution endpoint.
- All queries are parameterised via pyexasol named parameters.
- File uploads limited to 10 MB; only CSV and Excel accepted.
- CORS restricted to configured origins.
- Exasol credentials in `.env` (never committed).
- LLM output validated against schema before use; never used for financial figures.

## Deployment (single machine)

All components run on one machine:
- Exasol Personal in Podman container
- FastAPI via uvicorn
- Frontend via Vite dev server (or served as static files from dist/)

No cloud services, no message queues, no external data feeds required.
