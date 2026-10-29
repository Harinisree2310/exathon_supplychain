-- ============================================================
-- SupplyLens – Supplier Alternative Comparison
--
-- Feasibility rules (all must pass to be FEASIBLE):
--   1. unit_price_inr is known
--   2. required_qty >= min_order_qty when MOQ is known
--   3. required_qty <= max_capacity_qty when capacity is known
--   4. unknown capacity is CAPACITY_UNKNOWN (not proof of capacity)
--   5. lead_time_days <= max_acceptable_lead_time when known
--   6. quality_score >= min_quality_score when known
--   7. valid_until IS NULL OR valid_until >= CURRENT_DATE
--
-- Parameters: material_id, required_qty, max_acceptable_lead_time, min_quality_score
-- ============================================================
SELECT
    sq.quote_id,
    sq.material_id,
    m.material_name,
    sq.supplier_id,
    s.supplier_name,
    s.city,
    s.supplier_state,
    sq.unit_price_inr,
    sq.min_order_qty,
    sq.max_capacity_qty,
    sq.lead_time_days,
    sq.quality_score,
    sq.valid_until,
    sq.notes,
    CASE
        WHEN sq.unit_price_inr IS NULL
            THEN 'PRICE_UNKNOWN'
        WHEN sq.valid_until IS NOT NULL
         AND sq.valid_until < CURRENT_DATE
            THEN 'QUOTE_EXPIRED'
        WHEN sq.min_order_qty IS NOT NULL
         AND {required_qty} < sq.min_order_qty
            THEN 'MOQ_NOT_MET'
        WHEN sq.max_capacity_qty IS NULL
            THEN 'CAPACITY_UNKNOWN'
        WHEN {required_qty} > sq.max_capacity_qty
            THEN 'CAPACITY_EXCEEDED'
        WHEN sq.lead_time_days IS NULL
            THEN 'LEAD_TIME_UNKNOWN'
        WHEN sq.lead_time_days > {max_acceptable_lead_time}
            THEN 'LEAD_TIME_EXCEEDED'
        WHEN sq.quality_score IS NULL
            THEN 'QUALITY_UNKNOWN'
        WHEN sq.quality_score < {min_quality_score}
            THEN 'QUALITY_BELOW_THRESHOLD'
        ELSE 'FEASIBLE'
    END AS feasibility_status,
    RANK() OVER (
        PARTITION BY sq.material_id
        ORDER BY sq.unit_price_inr ASC
    ) AS price_rank
FROM SUPPLIER_QUOTATIONS sq
JOIN MATERIALS  m ON m.material_id  = sq.material_id
JOIN SUPPLIERS  s ON s.supplier_id  = sq.supplier_id
WHERE sq.material_id = {material_id}
ORDER BY sq.unit_price_inr ASC NULLS LAST;
