# SupplyLens Data Dictionary

## Tables

### SUPPLIERS
| Column | Type | Description |
|---|---|---|
| supplier_id | VARCHAR(36) | UUID primary key |
| supplier_name | VARCHAR(200) | Display name |
| gst_number | VARCHAR(15) | GSTIN (optional; synthetic demo data only) |
| city | VARCHAR(100) | City |
| supplier_state | VARCHAR(60) | Indian state |
| supplier_country | VARCHAR(60) | Default 'India' |
| supplier_tier | VARCHAR(20) | PREFERRED/APPROVED/BACKUP/SYNTHETIC |
| lead_time_days | DECIMAL(5,0) | Standard delivery lead time |
| quality_score | DECIMAL(4,2) | 0.00–10.00 |
| is_synthetic | BOOLEAN | TRUE for demo data |

### MATERIALS
| Column | Type | Description |
|---|---|---|
| material_id | VARCHAR(36) | UUID primary key |
| material_code | VARCHAR(50) | Material code (e.g. HR-STEEL-COIL; not unique-constrained by current DDL) |
| material_name | VARCHAR(200) | Human-readable name |
| category | VARCHAR(100) | e.g. Metals, Plastics |
| sub_category | VARCHAR(100) | e.g. Ferrous, Polyolefin |
| unit_of_measure | VARCHAR(20) | kg, MT, litre |
| normalised_name | VARCHAR(200) | Uppercase normalised for matching |

### PURCHASE_LINES
| Column | Type | Description |
|---|---|---|
| line_id | VARCHAR(36) | UUID primary key |
| po_number | VARCHAR(50) | Purchase order number |
| purchase_date | DATE | Date of purchase |
| material_id | VARCHAR(36) | FK → MATERIALS |
| supplier_id | VARCHAR(36) | FK → SUPPLIERS |
| quantity | DECIMAL(18,4) | Quantity in material's UOM |
| unit_price_inr | DECIMAL(18,4) | Price per UOM in INR |
| total_value_inr | DECIMAL(20,4) | quantity × unit_price_inr |
| currency | VARCHAR(3) | INR (default) |
| inr_exchange_rate | DECIMAL(12,6) | Rate at purchase date (1.0 for INR) |
| ingestion_id | VARCHAR(36) | Ingestion record identifier (no FK constraint in current DDL) |
| purchase_source | VARCHAR(20) | SYNTHETIC / CSV_UPLOAD |
| is_duplicate | BOOLEAN | TRUE if duplicate detected |

### MATERIAL_COMMODITY_MAP
| Column | Type | Description |
|---|---|---|
| map_id | VARCHAR(36) | UUID |
| material_id | VARCHAR(36) | FK → MATERIALS |
| commodity_code | VARCHAR(50) | e.g. BRENT_CRUDE, LME_COPPER |
| commodity_name | VARCHAR(200) | Human-readable commodity name |
| exposure_weight | DECIMAL(6,4) | Fraction 0–1; all weights for a material sum to 1.0 |
| mapping_basis | VARCHAR(200) | Documented justification |
| confidence | VARCHAR(20) | HIGH / MEDIUM / LOW |

### MARKET_SIGNALS
| Column | Type | Description |
|---|---|---|
| signal_id | VARCHAR(36) | UUID |
| commodity_code | VARCHAR(50) | e.g. BRENT_CRUDE |
| signal_date | DATE | Observation date |
| price | DECIMAL(18,6) | Price value |
| currency | VARCHAR(3) | USD, INR, MYR |
| unit | VARCHAR(30) | e.g. USD/barrel, USD/MT |
| signal_source | VARCHAR(100) | SYNTHETIC or data provider |

### SUPPLIER_QUOTATIONS
| Column | Type | Description |
|---|---|---|
| quote_id | VARCHAR(36) | UUID |
| supplier_id | VARCHAR(36) | FK → SUPPLIERS |
| material_id | VARCHAR(36) | FK → MATERIALS |
| quote_date | DATE | Date quotation was received |
| unit_price_inr | DECIMAL(18,4) | Quoted price per UOM in INR |
| min_order_qty | DECIMAL(18,4) | Minimum order quantity (MOQ) |
| max_capacity_qty | DECIMAL(18,4) | Maximum deliverable quantity per period |
| lead_time_days | DECIMAL(5,0) | Lead time for this quotation |
| quality_score | DECIMAL(4,2) | 0.00–10.00 |
| valid_until | DATE | Quotation expiry date (NULL = no expiry) |

### SCENARIO_RUNS
| Column | Type | Description |
|---|---|---|
| scenario_id | VARCHAR(36) | UUID |
| scenario_name | VARCHAR(200) | User-defined name |
| commodity_code | VARCHAR(50) | Commodity being shocked |
| shock_pct | DECIMAL(8,4) | Percentage magnitude of shock (0–100) |
| shock_direction | VARCHAR(4) | UP or DOWN |
| analysis_period_start | DATE | Spend observation window start |
| analysis_period_end | DATE | Spend observation window end |

### EXPOSURE_RESULTS
| Column | Type | Description |
|---|---|---|
| result_id | VARCHAR(36) | UUID |
| scenario_id | VARCHAR(36) | FK → SCENARIO_RUNS |
| material_id | VARCHAR(36) | FK → MATERIALS |
| commodity_code | VARCHAR(50) | Commodity driving exposure |
| exposure_weight | DECIMAL(6,4) | From MATERIAL_COMMODITY_MAP |
| observed_spend_inr | DECIMAL(22,4) | SUM(total_value_inr) in period |
| exposed_spend_inr | DECIMAL(22,4) | observed_spend × exposure_weight |
| incremental_cost_inr | DECIMAL(22,4) | exposed_spend × (shock_pct / 100) |

### RECOMMENDATIONS
| Column | Type | Description |
|---|---|---|
| recommendation_id | VARCHAR(36) | UUID |
| scenario_id | VARCHAR(36) | FK → SCENARIO_RUNS |
| material_id | VARCHAR(36) | FK → MATERIALS |
| action_code | VARCHAR(30) | SWITCH_SUPPLIER / SPLIT_ORDERS / VERIFY_FIRST / ACCEPT_COST / NO_ACTION |
| action_summary | VARCHAR(2000) | Human-readable explanation |
| confidence | VARCHAR(20) | HIGH / MEDIUM / LOW |
| requires_human_review | BOOLEAN | Always TRUE — system never auto-approves |
| alternative_supplier_id | VARCHAR(36) | Best feasible alternative (NULL if none) |
| estimated_saving_inr | DECIMAL(22,4) | NULL when unknown |
| saving_basis | VARCHAR(1000) | Methodology for saving estimate |
| evidence_summary | VARCHAR(4000) | Supplier feasibility and recommendation evidence |

### DECISION_EVENTS
| Column | Type | Description |
|---|---|---|
| decision_id | VARCHAR(36) | UUID |
| recommendation_id | VARCHAR(36) | FK → RECOMMENDATIONS |
| decision | VARCHAR(20) | APPROVED / REJECTED / DEFERRED |
| decided_by | VARCHAR(100) | Name or team recording the decision |
| decision_notes | VARCHAR(2000) | Free-text rationale |
| decided_at | TIMESTAMP | Decision timestamp |

### INGESTION_RECORDS
| Column | Type | Description |
|---|---|---|
| ingestion_id | VARCHAR(36) | UUID |
| file_name | VARCHAR(300) | Original filename |
| source_type | VARCHAR(30) | SYNTHETIC / CSV_UPLOAD / EXCEL_UPLOAD |
| row_count | DECIMAL(10,0) | Total rows in file |
| accepted_count | DECIMAL(10,0) | Rows successfully inserted |
| rejected_count | DECIMAL(10,0) | Rows with validation errors |
| duplicate_count | DECIMAL(10,0) | Rows identified as duplicates |
| ingest_status | VARCHAR(20) | PENDING / PROCESSING / COMPLETED / COMPLETED_WITH_ERRORS / FAILED |
| error_details | VARCHAR(4000) | Validation or ingestion error details |
| started_at | TIMESTAMP | Ingestion start time |
| completed_at | TIMESTAMP | Ingestion completion time |

## Views

| View | Description |
|---|---|
| V_MATERIAL_SPEND | Monthly spend by material |
| V_SUPPLIER_SHARE | Supplier share % per material |
| V_MATERIAL_HHI | HHI per material with concentration level |
| V_MATERIAL_EXPOSURE | Exposed spend per material-commodity pair |
| V_LATEST_MARKET_SIGNAL | Most recent signal per commodity |
| V_SUPPLIER_QUOTE_COMPARISON | Ranked quotations with price rank |
