# SupplyLens — 3-Minute Demo Script

## Setup (before demo)
1. Exasol Personal running (`irm https://www.exasol.com/install/starter-kit.ps1 | iex`)
2. Backend running: `cd backend && uvicorn app.main:app --reload`
3. Frontend running: `cd frontend && npm run dev`
4. Browser open at http://localhost:5173
5. Demo data NOT yet loaded (to show the loading step live)

---

## Shot 1 (0:00 – 0:30) — The Problem

**Screen:** Overview page (empty state)

*"Most Indian SMB manufacturers don't know which commodity price moves will hurt them most — or who they can switch to when they do. SupplyLens connects the dots from commodity shock to supplier decision in under 60 seconds."*

**Action:** Click "Data Workspace"

---

## Shot 2 (0:30 – 0:55) — Load Data into Exasol

**Screen:** Data Workspace

*"With one click, we load 6 months of purchase history, market signals and supplier quotations into Exasol Personal running locally."*

**Action:** Click "Load Demo Data"

*"Exasol ingests 84 purchase lines, 1,288 market price observations and 12 supplier quotations. The analytical queries run in Exasol."*

**Action:** Navigate to Overview

---

## Shot 3 (0:55 – 1:25) — Spot the Risk

**Screen:** Overview dashboard

*"The overview immediately shows ₹[X] lakhs in procurement spend, 6 exposed materials, and — critically — 1 material with dangerously high supplier concentration."*

**Action:** Point to concentration table showing M001 (Steel Coil) HHI 8180 — HIGH

*"Hot-Rolled Steel Coil is 90% sourced from one supplier. That's an HHI of 8,180. A monopoly score is 10,000. We are dangerously close."*

---

## Shot 4 (1:25 – 2:00) — Run a Scenario in Exasol

**Screen:** Scenario Lab

*"What if Brent Crude rises 15%? I'll create that scenario now."*

**Action:** Create scenario "Brent Crude +15% Shock" → Click "Run Calculation"

*"That SQL query runs inside Exasol. It joins our purchase data to commodity mappings, calculates exposed spend for each material, and computes the incremental cost. The formula: exposed spend × shock percentage."*

**Action:** Show results table + bar chart

*"Total estimated impact: ₹[X] lakhs — but only ₹[Y] lakhs is in materials we can act on quickly."*

---

## Shot 5 (2:00 – 2:35) — Supplier Alternatives

**Screen:** Supplier Comparison → Material: HDPE Granules (M002)

*"For HDPE, there are three quoted suppliers. Watch what happens when we apply the feasibility constraints."*

**Action:** Set required qty to 5000 → Observe NorthWest Plastics rejected

*"NorthWest Plastics is cheaper — but their maximum capacity is 1,500 kg/month against our 5,000 kg requirement. Rejected automatically. ChemSource Gujarat is our best feasible option."*

---

## Shot 6 (2:35 – 2:55) — Evidence and Decision

**Screen:** Evidence Trace → Select a recommendation

*"Every recommendation comes with a full evidence chain — market signal date, the mapping rule, the actual purchase lines, the SQL-computed exposure, and why each alternative was accepted or rejected."*

*"No black box. Every number is traceable."*

**Action:** Decision Review → Approve a recommendation

*"Decisions are recorded with the approver's name and timestamp. SupplyLens never places an order automatically."*

---

## Shot 7 (2:55 – 3:00) — Close

*"SupplyLens: from commodity shock to defensible procurement decision in under 3 minutes. Powered by Exasol Personal. Open source. Built for Indian SMBs."*

---

## Shot List

| Shot | Screen | Key Action | Key Message |
|---|---|---|---|
| 1 | Overview (empty) | — | Problem statement |
| 2 | Data Workspace | Load Demo Data | Exasol ingestion |
| 3 | Overview (loaded) | Point to HHI | Concentration risk visible |
| 4 | Scenario Lab | Create + Run | Exasol SQL + formula |
| 5 | Supplier Comparison | Filter constraints | Rejected alternative shown |
| 6 | Evidence Trace + Decision | Review chain | Transparency + human approval |
| 7 | (screen off) | — | Tagline |
