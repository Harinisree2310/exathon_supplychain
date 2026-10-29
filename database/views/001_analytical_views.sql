-- ============================================================
-- SupplyLens – Analytical Views
-- These are referenced by the query layer; they simplify
-- Python code and ensure calculations happen inside Exasol.
-- ============================================================

-- ── Material spend summary ────────────────────────────────────
CREATE OR REPLACE VIEW V_MATERIAL_SPEND AS
SELECT
    pl.material_id,
    m.material_code,
    m.material_name,
    m.category,
    m.unit_of_measure,
    DATE_TRUNC('MONTH', pl.purchase_date)  AS spend_month,
    SUM(pl.quantity)                        AS total_quantity,
    SUM(pl.total_value_inr)                 AS total_spend_inr,
    COUNT(DISTINCT pl.supplier_id)          AS distinct_supplier_count,
    COUNT(pl.line_id)                       AS line_count
FROM PURCHASE_LINES pl
JOIN MATERIALS m ON m.material_id = pl.material_id
WHERE pl.is_duplicate = FALSE
GROUP BY
    pl.material_id, m.material_code, m.material_name,
    m.category, m.unit_of_measure,
    DATE_TRUNC('MONTH', pl.purchase_date);

-- ── Supplier share per material ───────────────────────────────
-- Used for HHI calculation and concentration dashboards.
CREATE OR REPLACE VIEW V_SUPPLIER_SHARE AS
SELECT
    pl.material_id,
    m.material_name,
    pl.supplier_id,
    s.supplier_name,
    SUM(pl.total_value_inr)                            AS supplier_spend_inr,
    SUM(SUM(pl.total_value_inr)) OVER (PARTITION BY pl.material_id)
                                                        AS total_material_spend_inr,
    ROUND(
        SUM(pl.total_value_inr) /
        SUM(SUM(pl.total_value_inr)) OVER (PARTITION BY pl.material_id) * 100,
    2)                                                  AS share_pct,
    -- HHI contribution: share_pct^2
    ROUND(
        POWER(
            SUM(pl.total_value_inr) /
            SUM(SUM(pl.total_value_inr)) OVER (PARTITION BY pl.material_id) * 100,
        2),
    4)                                                  AS hhi_contribution
FROM PURCHASE_LINES pl
JOIN MATERIALS m  ON m.material_id  = pl.material_id
JOIN SUPPLIERS s  ON s.supplier_id  = pl.supplier_id
WHERE pl.is_duplicate = FALSE
GROUP BY pl.material_id, m.material_name, pl.supplier_id, s.supplier_name;

-- ── Material HHI (one row per material) ──────────────────────
CREATE OR REPLACE VIEW V_MATERIAL_HHI AS
SELECT
    material_id,
    material_name,
    SUM(hhi_contribution)  AS hhi,
    COUNT(*)               AS supplier_count,
    MAX(share_pct)         AS dominant_share_pct,
    CASE
        WHEN SUM(hhi_contribution) > 2500 THEN 'HIGH'
        WHEN SUM(hhi_contribution) > 1500 THEN 'MEDIUM'
        ELSE 'LOW'
    END                    AS concentration_level
FROM V_SUPPLIER_SHARE
GROUP BY material_id, material_name;

-- ── Material exposure to market commodities ───────────────────
CREATE OR REPLACE VIEW V_MATERIAL_EXPOSURE AS
SELECT
    ms.material_id,
    ms.material_name,
    ms.total_spend_inr,
    mcm.commodity_code,
    mcm.commodity_name,
    mcm.exposure_weight,
    mcm.confidence,
    ROUND(ms.total_spend_inr * mcm.exposure_weight, 4) AS exposed_spend_inr
FROM (
    SELECT material_id, material_name, SUM(total_spend_inr) AS total_spend_inr
    FROM V_MATERIAL_SPEND
    GROUP BY material_id, material_name
) ms
JOIN MATERIAL_COMMODITY_MAP mcm ON mcm.material_id = ms.material_id;

-- ── Latest market signal per commodity ───────────────────────
CREATE OR REPLACE VIEW V_LATEST_MARKET_SIGNAL AS
SELECT
    ms.*
FROM MARKET_SIGNALS ms
JOIN (
    SELECT commodity_code, MAX(signal_date) AS latest_date
    FROM MARKET_SIGNALS
    GROUP BY commodity_code
) latest ON latest.commodity_code = ms.commodity_code
         AND latest.latest_date   = ms.signal_date;

-- ── Supplier quotation comparison ─────────────────────────────
CREATE OR REPLACE VIEW V_SUPPLIER_QUOTE_COMPARISON AS
SELECT
    sq.material_id,
    m.material_name,
    sq.supplier_id,
    s.supplier_name,
    sq.quote_date,
    sq.unit_price_inr,
    sq.min_order_qty,
    sq.max_capacity_qty,
    sq.lead_time_days,
    sq.quality_score,
    sq.valid_until,
    -- Rank by unit price ascending (cheapest first)
    RANK() OVER (
        PARTITION BY sq.material_id
        ORDER BY sq.unit_price_inr ASC
    ) AS price_rank
FROM SUPPLIER_QUOTATIONS sq
JOIN MATERIALS  m ON m.material_id  = sq.material_id
JOIN SUPPLIERS  s ON s.supplier_id  = sq.supplier_id
WHERE sq.valid_until IS NULL OR sq.valid_until >= CURRENT_DATE;
