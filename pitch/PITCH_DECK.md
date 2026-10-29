# SupplyLens — Pitch Deck
## ExaThon India 2026

---

### Slide 1 — Title
**SupplyLens**
*Shock-to-Decision Intelligence for Indian SMBs*

Powered by Exasol Personal | Open Source | ExaThon India 2026

---

### Slide 2 — The Problem
**Indian SMB manufacturers face commodity price shocks with no tools.**

- 63 million MSMEs contribute 30% of India's GDP
- Raw material costs = 60–70% of manufacturing cost
- When Brent Crude jumps 20%, a plastics manufacturer has no idea:
  - Which materials are exposed?
  - By how much?
  - Can they switch suppliers? Can those suppliers actually deliver?

**Result:** Reactive decisions, missed savings, concentrated supplier risk.

---

### Slide 3 — The Solution
**SupplyLens** lets a user model a hypothetical commodity shock against
purchase history, evaluates supplier alternatives against hard constraints,
and generates a recommended action with traceable evidence.

*From a user-defined commodity shock to an auditable procurement decision.*

---

### Slide 4 — How It Works (Workflow)

```
Market History (context) + User-Defined Shock
     ↓
Material Mapping (exposure weights)
     ↓
Purchase Evidence (Exasol: 6 months of data)
     ↓
Exposure Calculation (Exasol SQL)
     ↓
Supplier Comparison (feasibility constraints)
     ↓
Recommendation + Evidence Trace
     ↓
Human Decision (approved/rejected/deferred)
```

---

### Slide 5 — Exasol at the Core

**Why Exasol?**
- Exasol SQL: HHI, exposure calculations and multi-table joins run in the database
- Parameterised SQL: safe, auditable, no arbitrary execution
- Local database workflow; optional external LLM explanation is not wired into the current API
- `pyexasol`: official Python driver, WebSocket-based, no ODBC

**What Exasol does in SupplyLens:**
- Aggregates 6 months of purchase data by material and supplier
- Calculates Herfindahl–Hirschman Index for concentration risk
- Executes scenario impact query (JOIN across 4 tables)
- Evaluates supplier feasibility with parameterised constraints
- Persists scenario results for reproducibility

---

### Slide 6 — Key Differentiators

| Feature | SupplyLens | Spreadsheet | ERP Module |
|---|---|---|---|
| Commodity exposure mapping | ✅ Transparent rules | ❌ Manual | ⚠️ Black box |
| Supplier feasibility check | ✅ Hard constraints | ❌ Manual | ⚠️ Partial |
| Evidence trace | ✅ Full chain | ❌ | ❌ |
| Data stays local | ✅ Exasol Personal | N/A | ❌ Cloud |
| No real data required | ✅ Synthetic demo | N/A | ❌ Requires ERP data |
| Open source | ✅ MIT | N/A | ❌ |

---

### Slide 7 — Demonstration Results (Synthetic Data, seed=42)

| Metric | Value | Source |
|---|---|---|
| Total purchase spend (6 months) | ₹2.92 Crore | Synthetic reference calculation |
| M001 (Steel Coil) HHI | 8,180 — HIGH | Synthetic reference calculation |
| M001 dominant supplier share | 89.9% | Synthetic reference calculation |
| SC001 (Brent +15%) incremental cost | ₹5.4 Lakhs | Synthetic reference calculation |
| NorthWest Plastics (M002) | REJECTED — capacity | Synthetic quote constraints |

*All data is synthetic. Values are Python-generated reference outputs; live Exasol comparison remains pending.*

---

### Slide 8 — Technical Excellence

- **12 Exasol tables**
- **6 analytical views** (HHI, exposure, supplier share)
- **2 parameterised SQL queries** for scenario impact and supplier comparison
- **FastAPI** with Pydantic v2 validation
- **49 tests passed; 3 live-Exasol tests skipped** at the latest audit run
- **TypeScript frontend** — strict TypeScript build
- Full **evidence chain** from market signal to decision record

---

### Slide 9 — User Experience

8 screens covering the full workflow:
1. **Overview** — spend, concentration, exposure at a glance
2. **Data Workspace** — load demo or upload your own CSV
3. **Material Risk Explorer** — spend vs commodity price history
4. **Scenario Lab** — configure and run shocks, compare baseline vs shocked
5. **Supplier Comparison** — hard constraints surfaced explicitly
6. **Evidence Trace** — inspect every number's provenance
7. **Decision Review** — approve/reject with signature and notes
8. **Reports** — export a full JSON summary or a compact CSV exposure table

---

### Slide 10 — Open Source & Next Steps

**Today (MVP):**
- Synthetic demo workflow implemented; live Exasol acceptance is pending
- MIT licence, documented API, backend tests and frontend production build

**Next:**
- Real GST authorised-file ingestion
- PDF report export
- Docker Compose packaging
- GSTN-linked material normalisation
- Live market data connectors (MCX, BMD)

**Repository:** github.com/[team]/supplylens

*Built for Indian SMBs. Powered by Exasol. Open to all.*
