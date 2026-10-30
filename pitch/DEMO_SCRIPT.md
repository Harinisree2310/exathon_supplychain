





























































      # SupplyLens — Demo Video Script

**Target length:** 3–4 minutes
**Audience:** ExaThon judges, manufacturing leaders and potential users
**Demo URL:** `http://127.0.0.1:5173`

## Before recording

- Start Exasol Personal, the backend and the frontend. Confirm the Overview page
  says **Database connected**.
- Load the synthetic demo dataset in **Data Workspace** before recording. It
  contains 84 purchase lines, 1,288 simulated market-price observations, six
  materials and seven suppliers. Avoid `Reset & Reload` during the recording.
- Use a clean browser window at desktop size. Keep the frontend as the only
  visible window; do not show terminals, credentials or other open tabs.
- The current demo data shows approximately **₹2.92 crore** in spend. Values
  can change if the dataset is reloaded; verify the live figures before
  recording.
- The sample already contains a saved **Brent Crude +15% Shock** scenario.
  Running it over the July 2025–January 2026 period currently shows about
  **₹5.45 lakh** in estimated incremental cost.
- In **Supplier Comparison**, select **HDPE Granules**, set required quantity
  to **5,000**, maximum lead time to **30 days**, and minimum quality to **6**.
  NorthWest Plastics should be rejected for capacity (1,500); ChemSource
  Gujarat and GreenField Polymers meet the displayed constraints.
- A recorded decision is persisted. Use only the synthetic demo workspace if
  you choose to record one.
- **GSTIN accuracy:** GSTIN is an optional supplier field in the data model.
  This demo does not connect to GSTN, verify GSTINs, or ingest GST returns or
  invoices. Describe GSTIN as a potential supplier-identity/reconciliation
  key for a future, explicitly authorized integration—not as a feature that
  has already been implemented.

## Script and shot list

### 0:00–0:25 — Hook and idea

**Window:** SupplyLens **Overview**. Start with the dashboard visible; camera
optional.

**Say:**

> A commodity price shock is not just a headline. For a manufacturer, the real
> questions are: which materials are exposed, how much could it cost us, and
> can an alternative supplier actually deliver? SupplyLens connects those
> questions—from a hypothetical market shock to an evidence-backed procurement
> decision.

### 0:25–0:55 — What makes it different

**Window:** Stay on **Overview**; point to total spend and supplier
concentration.

**Say:**

> A spreadsheet can calculate a number. A market chart can show a price move.
> A purchasing system can record an order. SupplyLens is designed to connect
> those steps: it maps materials to commodity exposure, tests supplier
> alternatives against practical constraints, and lets a person inspect the
> evidence behind the recommendation. It complements an ERP; it is not a
> replacement for one.

> The key differentiator is the traceable shock-to-decision workflow—not an
> unexplained forecast or an automatic order.

### 0:55–1:10 — Data foundation

**Window:** Click **Data workspace**. Show the demo dataset and data-quality
summary; do not reload it.

**Say:**

> This workspace is running on synthetic data: 84 purchase lines, 1,288
> simulated market observations, and six mapped materials. The live demo uses
> Exasol for the analytical queries. No real company or GST data is being used.

### 1:10–1:40 — Surface a risk

**Window:** Click **Material risk**. Select **Hot-Rolled Steel Coil** if
available; show the material table and concentration indicator.

**Say:**

> Here we can inspect purchase history alongside commodity signals. In this
> sample, Hot-Rolled Steel Coil has an HHI of about 8,180 and roughly 90% of
> its spend with one supplier. HHI runs up to 10,000 for a single-source
> monopoly, so this is a clear concentration warning—not a prediction of
> disruption.

### 1:40–2:15 — Model a shock

**Window:** Click **Scenario lab**. Select the saved **Brent Crude +15% Shock**
scenario and click **Run Calculation**. Show the results chart/table.

**Say:**

> Now let’s ask a what-if question: what if Brent Crude rose 15% over the
> analysis period? SupplyLens joins historical spend with documented
> material-to-commodity exposure weights and calculates the impact in Exasol.
> In this dataset, the estimated incremental cost is about ₹5.45 lakh.

> This is a transparent scenario estimate using a linear pass-through
> assumption—not a market forecast or a promise of actual costs.

### 2:15–2:45 — Check whether an alternative is viable

**Window:** Click **Suppliers**. Choose **HDPE Granules** and set the required
quantity to **5,000**; maximum lead time **30** and minimum quality **6**.
Point to feasible and rejected alternatives.

**Say:**

> The cheapest quote is not automatically the right answer. At a requirement
> of 5,000, NorthWest Plastics is rejected because its listed capacity is
> 1,500. The other sample quotations meet these displayed constraints. The
> rule is explicit: compare price, capacity, minimum order, lead time and
> quality—not price alone.

### 2:45–3:20 — Evidence, human review and GSTIN

**Window:** Click **Evidence trace** and select a recommendation. Then open
**Decision review** without recording a decision unless you intend to persist
one in the synthetic demo database.

**Say:**

> Every recommendation can be traced through the scenario, market signal,
> material mapping, purchase evidence, exposure calculation and supplier
> alternatives. A reviewer can inspect that chain before recording a decision.
> The system does not place orders or approve recommendations automatically.

> One important scope note: GSTIN is an optional supplier field in our data
> model, but GSTN verification and GST-document ingestion are not implemented
> in this demo. In a future authorized integration, GSTIN could help reconcile
> supplier identities across records. It identifies a registered business;
> it does not prove a supplier’s capacity, quality or quote.

### 3:20–3:35 — Close

**Window:** Return to **Overview**.

**Say:**

> SupplyLens turns a commodity what-if into a supplier-aware, auditable
> decision workflow for Indian manufacturers. The differentiator is the
> connection from shock to evidence to human decision. This is a local,
> synthetic-data prototype powered by Exasol Personal—and a foundation for
> trusted procurement intelligence.

## Product positioning: quick reference

- **Primary USP:** a transparent chain from a user-defined commodity shock to
  material-level exposure, supplier feasibility and a human-reviewed decision.
- **Compared with a spreadsheet:** less manual joining and constraint checking;
  results have a structured evidence trail.
- **Compared with a standalone commodity dashboard:** connects a market signal
  to the buyer's material and purchase exposure.
- **Compared with ERP/procurement software:** demonstrates scenario analysis
  and evidence-focused supplier comparison; it complements operational
  transaction systems rather than claiming to replace them.
- **GSTIN's role today:** optional supplier identity field only; not used by the
  scenario calculation and not verified against GSTN.
- **GSTIN's potential future role:** with user authorization and a compliant
  integration, help match supplier identities across purchase and tax records.
  It is not, by itself, proof of supply capacity, quality, or pricing.
- **Claims to avoid:** live GSTN integration, verified GST data, real market
  feeds, actual cost forecasts, guaranteed savings, or a claim that no other
  product offers these capabilities.
