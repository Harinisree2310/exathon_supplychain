-- ============================================================
-- SupplyLens  –  Core Table Definitions  (Exasol 2026.x)
-- ============================================================

CREATE TABLE IF NOT EXISTS SUPPLIERS (
    supplier_id       VARCHAR(36)     NOT NULL,
    supplier_name     VARCHAR(200)    NOT NULL,
    gst_number        VARCHAR(15),
    city              VARCHAR(100),
    supplier_state    VARCHAR(60),
    supplier_country  VARCHAR(60)     DEFAULT 'India',
    supplier_tier     VARCHAR(20),
    lead_time_days    DECIMAL(5,0),
    quality_score     DECIMAL(4,2),
    is_synthetic      BOOLEAN         DEFAULT TRUE,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_suppliers PRIMARY KEY (supplier_id)
);

CREATE TABLE IF NOT EXISTS MATERIALS (
    material_id       VARCHAR(36)     NOT NULL,
    material_code     VARCHAR(50)     NOT NULL,
    material_name     VARCHAR(200)    NOT NULL,
    category          VARCHAR(100),
    sub_category      VARCHAR(100),
    unit_of_measure   VARCHAR(20)     DEFAULT 'kg',
    normalised_name   VARCHAR(200),
    is_synthetic      BOOLEAN         DEFAULT TRUE,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_materials PRIMARY KEY (material_id)
    -- CONSTRAINT uq_material_code UNIQUE (material_code) -- removed for Exasol compatibility
);

CREATE TABLE IF NOT EXISTS PURCHASE_LINES (
    line_id           VARCHAR(36)     NOT NULL,
    po_number         VARCHAR(50),
    purchase_date     DATE            NOT NULL,
    material_id       VARCHAR(36)     NOT NULL,
    supplier_id       VARCHAR(36)     NOT NULL,
    quantity          DECIMAL(18,4)   NOT NULL,
    unit_price_inr    DECIMAL(18,4)   NOT NULL,
    total_value_inr   DECIMAL(20,4)   NOT NULL,
    currency          VARCHAR(3)      DEFAULT 'INR',
    inr_exchange_rate DECIMAL(12,6)   DEFAULT 1.0,
    ingestion_id      VARCHAR(36),
    purchase_source   VARCHAR(20)     DEFAULT 'SYNTHETIC',
    is_duplicate      BOOLEAN         DEFAULT FALSE,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_purchase_lines PRIMARY KEY (line_id),
    CONSTRAINT fk_pl_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id),
    CONSTRAINT fk_pl_supplier FOREIGN KEY (supplier_id) REFERENCES SUPPLIERS(supplier_id)
);

CREATE TABLE IF NOT EXISTS MATERIAL_COMMODITY_MAP (
    map_id            VARCHAR(36)     NOT NULL,
    material_id       VARCHAR(36)     NOT NULL,
    commodity_code    VARCHAR(50)     NOT NULL,
    commodity_name    VARCHAR(200)    NOT NULL,
    exposure_weight   DECIMAL(6,4)    NOT NULL,
    mapping_basis     VARCHAR(500),
    confidence        VARCHAR(20)     DEFAULT 'HIGH',
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_mcm PRIMARY KEY (map_id),
    CONSTRAINT fk_mcm_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id)
);

CREATE TABLE IF NOT EXISTS MARKET_SIGNALS (
    signal_id         VARCHAR(36)     NOT NULL,
    commodity_code    VARCHAR(50)     NOT NULL,
    signal_date       DATE            NOT NULL,
    price             DECIMAL(18,6)   NOT NULL,
    currency          VARCHAR(3)      DEFAULT 'USD',
    unit              VARCHAR(30),
    signal_source     VARCHAR(100)    DEFAULT 'SYNTHETIC',
    is_synthetic      BOOLEAN         DEFAULT TRUE,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_market_signals PRIMARY KEY (signal_id)

);

CREATE TABLE IF NOT EXISTS SUPPLIER_QUOTATIONS (
    quote_id          VARCHAR(36)     NOT NULL,
    supplier_id       VARCHAR(36)     NOT NULL,
    material_id       VARCHAR(36)     NOT NULL,
    quote_date        DATE            NOT NULL,
    unit_price_inr    DECIMAL(18,4)   NOT NULL,
    min_order_qty     DECIMAL(18,4),
    max_capacity_qty  DECIMAL(18,4),
    lead_time_days    DECIMAL(5,0),
    quality_score     DECIMAL(4,2),
    valid_until       DATE,
    is_synthetic      BOOLEAN         DEFAULT TRUE,
    notes             VARCHAR(500),
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_supplier_quotations PRIMARY KEY (quote_id),
    CONSTRAINT fk_sq_supplier FOREIGN KEY (supplier_id) REFERENCES SUPPLIERS(supplier_id),
    CONSTRAINT fk_sq_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id)
);

CREATE TABLE IF NOT EXISTS SCENARIO_RUNS (
    scenario_id           VARCHAR(36)     NOT NULL,
    scenario_name         VARCHAR(200)    NOT NULL,
    commodity_code        VARCHAR(50)     NOT NULL,
    shock_pct             DECIMAL(8,4)    NOT NULL,
    shock_direction       VARCHAR(4)      DEFAULT 'UP',
    analysis_period_start DATE,
    analysis_period_end   DATE,
    created_at            TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    created_by            VARCHAR(100)    DEFAULT 'system',
    CONSTRAINT pk_scenario_runs PRIMARY KEY (scenario_id)
);

CREATE TABLE IF NOT EXISTS EXPOSURE_RESULTS (
    result_id             VARCHAR(36)     NOT NULL,
    scenario_id           VARCHAR(36)     NOT NULL,
    material_id           VARCHAR(36)     NOT NULL,
    commodity_code        VARCHAR(50)     NOT NULL,
    exposure_weight       DECIMAL(6,4)    NOT NULL,
    observed_spend_inr    DECIMAL(22,4)   NOT NULL,
    exposed_spend_inr     DECIMAL(22,4)   NOT NULL,
    incremental_cost_inr  DECIMAL(22,4)   NOT NULL,
    calculation_ts        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_exposure_results PRIMARY KEY (result_id),
    CONSTRAINT fk_er_scenario FOREIGN KEY (scenario_id) REFERENCES SCENARIO_RUNS(scenario_id),
    CONSTRAINT fk_er_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id)
);

CREATE TABLE IF NOT EXISTS SUPPLIER_CONCENTRATION (
    concentration_id   VARCHAR(36)     NOT NULL,
    material_id        VARCHAR(36)     NOT NULL,
    supplier_id        VARCHAR(36)     NOT NULL,
    period_start       DATE            NOT NULL,
    period_end         DATE            NOT NULL,
    supplier_spend_inr DECIMAL(22,4)   NOT NULL,
    total_spend_inr    DECIMAL(22,4)   NOT NULL,
    share_pct          DECIMAL(8,4)    NOT NULL,
    hhi                DECIMAL(10,4),
    calculated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_supplier_concentration PRIMARY KEY (concentration_id),
    CONSTRAINT fk_sc_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id),
    CONSTRAINT fk_sc_supplier FOREIGN KEY (supplier_id) REFERENCES SUPPLIERS(supplier_id)
);

CREATE TABLE IF NOT EXISTS RECOMMENDATIONS (
    recommendation_id       VARCHAR(36)     NOT NULL,
    scenario_id             VARCHAR(36)     NOT NULL,
    material_id             VARCHAR(36)     NOT NULL,
    action_code             VARCHAR(30)     NOT NULL,
    action_summary          VARCHAR(2000)   NOT NULL,
    confidence              VARCHAR(20)     DEFAULT 'MEDIUM',
    requires_human_review   BOOLEAN         DEFAULT TRUE,
    alternative_supplier_id VARCHAR(36),
    estimated_saving_inr    DECIMAL(22,4),
    saving_basis            VARCHAR(1000),
    evidence_summary        VARCHAR(4000),
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_recommendations PRIMARY KEY (recommendation_id),
    CONSTRAINT fk_rec_scenario FOREIGN KEY (scenario_id) REFERENCES SCENARIO_RUNS(scenario_id),
    CONSTRAINT fk_rec_material FOREIGN KEY (material_id) REFERENCES MATERIALS(material_id)
);

CREATE TABLE IF NOT EXISTS DECISION_EVENTS (
    decision_id       VARCHAR(36)     NOT NULL,
    recommendation_id VARCHAR(36)     NOT NULL,
    decision          VARCHAR(20)     NOT NULL,
    decided_by        VARCHAR(100)    NOT NULL,
    decision_notes    VARCHAR(2000),
    decided_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_decision_events PRIMARY KEY (decision_id),
    CONSTRAINT fk_de_recommendation FOREIGN KEY (recommendation_id) REFERENCES RECOMMENDATIONS(recommendation_id)
);

CREATE TABLE IF NOT EXISTS INGESTION_RECORDS (
    ingestion_id      VARCHAR(36)     NOT NULL,
    file_name         VARCHAR(300),
    source_type       VARCHAR(30)     NOT NULL,
    row_count         DECIMAL(10,0),
    accepted_count    DECIMAL(10,0),
    rejected_count    DECIMAL(10,0),
    duplicate_count   DECIMAL(10,0),
    ingest_status     VARCHAR(20)     DEFAULT 'PENDING',
    error_details     VARCHAR(4000),
    started_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    completed_at      TIMESTAMP,
    CONSTRAINT pk_ingestion_records PRIMARY KEY (ingestion_id)
);
