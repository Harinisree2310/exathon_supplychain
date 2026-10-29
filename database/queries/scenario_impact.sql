-- ============================================================
-- SupplyLens – Scenario Impact Query
--
-- Formula:
--   observed_spend   = SUM(total_value_inr) for the material over period
--   exposed_spend    = observed_spend × exposure_weight
--   signed_shock_pct = +shock_pct if UP, -shock_pct if DOWN (applied once)
--   incremental_cost = exposed_spend × (signed_shock_pct / 100)
--
-- Only materials mapped to the scenario commodity are included.
-- Parameters use PyExasol's named-placeholder syntax:
--   scenario_id, period_start, period_end
-- ============================================================
SELECT
    sr.scenario_id,
    sr.scenario_name,
    sr.commodity_code,
    sr.shock_pct,
    sr.shock_direction,
    CASE
        WHEN UPPER(sr.shock_direction) = 'DOWN' THEN -ABS(sr.shock_pct)
        ELSE ABS(sr.shock_pct)
    END AS signed_shock_pct,
    me.material_id,
    m.material_name,
    me.exposure_weight,
    me.confidence              AS mapping_confidence,
    COALESCE(period_spend.observed_spend_inr, 0)         AS observed_spend_inr,
    ROUND(
        COALESCE(period_spend.observed_spend_inr, 0) * me.exposure_weight,
    4)                                                    AS exposed_spend_inr,
    ROUND(
        COALESCE(period_spend.observed_spend_inr, 0)
        * me.exposure_weight
        * (
            CASE
                WHEN UPPER(sr.shock_direction) = 'DOWN' THEN -ABS(sr.shock_pct)
                ELSE ABS(sr.shock_pct)
            END
            / 100.0
          ),
    4)                                                    AS incremental_cost_inr,
    COALESCE(period_spend.line_count, 0)                 AS line_count,
    COALESCE(period_spend.distinct_supplier_count, 0)    AS distinct_supplier_count
FROM SCENARIO_RUNS sr
JOIN MATERIAL_COMMODITY_MAP me
    ON me.commodity_code = sr.commodity_code
JOIN MATERIALS m
    ON m.material_id = me.material_id
LEFT JOIN (
    SELECT
        pl.material_id,
        SUM(pl.total_value_inr)        AS observed_spend_inr,
        COUNT(pl.line_id)              AS line_count,
        COUNT(DISTINCT pl.supplier_id) AS distinct_supplier_count
    FROM PURCHASE_LINES pl
    WHERE pl.is_duplicate = FALSE
      AND pl.purchase_date BETWEEN {period_start} AND {period_end}
    GROUP BY pl.material_id
) period_spend ON period_spend.material_id = me.material_id
WHERE sr.scenario_id = {scenario_id}
ORDER BY exposed_spend_inr DESC;
