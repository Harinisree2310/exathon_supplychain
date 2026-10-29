# SupplyLens Calculation Methodology

## 1. Observed Purchase Spend

**Definition:** The total value of non-duplicate purchase lines for a material within the analysis period.

```
observed_spend = SUM(total_value_inr)
  WHERE material_id = :material_id
    AND is_duplicate = FALSE
    AND purchase_date BETWEEN :period_start AND :period_end
```

`total_value_inr` is recorded at the time of purchase: `quantity × unit_price_inr`.
No currency conversion is applied unless the original transaction was in a non-INR currency.

---

## 2. Exposed Spend

**Definition:** The fraction of observed spend that is economically linked to a specific commodity.

```
exposed_spend = observed_spend × exposure_weight
```

`exposure_weight` is the proportion of the material's cost that tracks a commodity index.
Weights are documented in `MATERIAL_COMMODITY_MAP.mapping_basis` and must sum to 1.0 per material.

**Example:** HDPE Granules (M002)
- 70% exposed to Naphtha Spot (primary feedstock)
- 30% exposed to Brent Crude (upstream energy)

---

## 3. Incremental Cost Under a Shock

**Definition:** The estimated additional procurement cost if the commodity price changes by the shock percentage.

```
incremental_cost = exposed_spend × (shock_pct / 100)
```

**Assumptions (must be disclosed):**
- Linear price pass-through — a 15% commodity rise increases material cost by 15% × exposure_weight.
- Market spot prices are the relevant price signal. Contract terms, hedging and inventory buffers are not modelled.
- The analysis period's historical spend is used as the baseline. Future volumes may differ.

**What this is NOT:**
- Not a forecast of actual cost increases.
- Not adjusted for contract terms, fixed-price periods or hedging.
- Not validated against real market data.

---

## 4. Supplier Concentration (HHI)

**Definition:** The Herfindahl–Hirschman Index measures the concentration of purchase spend across suppliers for a given material.

```
share_i = supplier_spend_i / total_material_spend × 100
HHI = SUM( share_i ^ 2 )
```

**Interpretation:**
| HHI Range | Concentration Level |
|---|---|
| 0 – 1,499 | LOW (competitive market) |
| 1,500 – 2,499 | MEDIUM (moderate concentration) |
| 2,500 – 10,000 | HIGH (concentrated, single-source risk) |

A monopoly supplier = HHI of 10,000. Equal duopoly = HHI of 5,000.

---

## 5. Supplier Feasibility Evaluation

A supplier alternative is FEASIBLE only if all of the following conditions are met:

| Check | Condition |
|---|---|
| Price known | `unit_price_inr IS NOT NULL` |
| MOQ met | `required_qty >= min_order_qty` |
| Capacity sufficient | `required_qty <= max_capacity_qty OR max_capacity_qty IS NULL` |
| Lead time acceptable | `lead_time_days <= max_acceptable_lead_time` |
| Quality acceptable | `quality_score >= min_quality_score` |
| Quote not expired | `valid_until IS NULL OR valid_until >= CURRENT_DATE` |

Missing capacity data is treated as **unknown**, not unlimited. The SQL feasibility
query returns `CAPACITY_UNKNOWN` for a quotation with NULL capacity, so it cannot
be recommended as a confirmed feasible alternative until its capacity is verified.

---

## 6. Saving Estimate

**Definition:** The potential reduction in procurement cost from switching to a lower-priced feasible alternative.

```
estimated_saving = (current_volume_weighted_unit_price - alternative_unit_price) × required_qty
```

The current volume-weighted unit price is calculated in Exasol as
`SUM(total_value_inr) / SUM(quantity)` across non-duplicate historical purchase
lines. `required_qty` is the quantity supplied for the recommendation (defaults
to 1,000 in the API).

**Conditions for calculation:**
1. Both current average price and alternative price must be known (not NULL).
2. Alternative must be FEASIBLE.
3. Alternative price must be strictly less than current average price.

**If conditions are not met, `estimated_saving_inr` is NULL.** The system never invents a saving figure.

**Caveats:**
- Current unit price is volume-weighted over historical purchase lines, not a negotiated contract price.
- Alternative price is from a quotation with a specific validity period.
- Actual savings depend on: negotiated volume discounts, delivery costs, quality acceptance, commercial terms.
- This is an indicative upper bound, not a financial commitment.

---

## 7. Evidence Quality

Each recommendation carries a confidence level:

| Level | Meaning |
|---|---|
| HIGH | Multiple feasible alternatives with known prices and capacity |
| MEDIUM | One feasible alternative; price and capacity verified |
| LOW | No feasible alternative, or critical data (capacity, quality) is missing |

**Human review is always required.** The system sets `requires_human_review = TRUE` on every recommendation without exception.

---

## 8. What SupplyLens Does Not Do

- Does not provide financial advice, legal counsel or procurement contracts.
- Does not place orders or initiate supplier communications.
- Does not access real GST data, real market feeds or real company financials.
- Does not predict future commodity prices.
- Does not validate supplier quality or capacity claims.
- Does not account for geopolitical risk, force majeure or ESG considerations.
