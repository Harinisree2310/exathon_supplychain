// ── API response types mirroring backend Pydantic schemas ──────────────────

export interface HealthStatus {
  api: string
  database: 'connected' | 'degraded' | 'unchecked'
  database_dsn: string
  version: string
  environment: string
}

export interface Material {
  material_id: string
  material_code: string
  material_name: string
  category: string | null
  sub_category: string | null
  unit_of_measure: string
  normalised_name: string | null
}

export interface Supplier {
  supplier_id: string
  supplier_name: string
  city: string | null
  state: string | null
  supplier_tier: string | null
  lead_time_days: number | null
  quality_score: number | null
}

export interface MarketSignal {
  signal_id: string
  commodity_code: string
  signal_date: string
  price: number
  currency: string
  unit: string | null
  source: string
}

export interface ConcentrationResult {
  material_id: string
  material_name: string
  hhi: number
  concentration_level: 'HIGH' | 'MEDIUM' | 'LOW'
  supplier_count: number
  dominant_share_pct: number
}

export interface Scenario {
  scenario_id: string
  scenario_name: string
  commodity_code: string
  shock_pct: number
  shock_direction: 'UP' | 'DOWN'
  analysis_period_start: string | null
  analysis_period_end: string | null
  created_at: string | null
}

export interface ExposureResult {
  material_id: string
  material_name: string
  commodity_code: string
  commodity_name: string
  exposure_weight: number
  mapping_confidence: string
  observed_spend_inr: number
  exposed_spend_inr: number
  incremental_cost_inr: number
  line_count: number | null
  distinct_supplier_count: number | null
}

export interface SupplierQuote {
  quote_id: string
  supplier_id: string
  supplier_name: string
  material_id: string
  material_name: string
  unit_price_inr: number
  min_order_qty: number | null
  max_capacity_qty: number | null
  lead_time_days: number | null
  quality_score: number | null
  valid_until: string | null
  feasibility_status: string
  price_rank: number
  notes: string | null
}

export interface Recommendation {
  recommendation_id: string
  scenario_id: string
  material_id: string
  action_code: string
  action_summary: string
  confidence: string
  requires_human_review: boolean
  alternative_supplier_id: string | null
  estimated_saving_inr: number | null
  saving_basis: string | null
  evidence_summary: string | null
}

export interface DataQuality {
  total_materials: number
  total_suppliers: number
  total_purchase_lines: number
  total_market_signals: number
  materials_with_mapping: number
  materials_without_mapping: number
  stale_signal_count: number
  incomplete_quotations: number
}

export interface PurchaseUploadResult {
  success: boolean
  message: string
  data: {
    total_rows: number
    accepted: number
    rejected: number
    duplicates: number
    rejected_details?: { row: number; errors: string[] }[]
  }
}

export interface OverviewStats {
  total_purchase_spend_inr: number
  exposed_material_count: number
  high_concentration_materials: number
  supplier_count: number
  latest_scenario: string | null
}

export interface SpendHistory {
  material_id: string | null
  history: { month: string; spend_inr: number }[]
}

export interface EvidenceTrace {
  recommendation_id: string
  material_id: string
  material_name: string
  action_code: string
  action_summary: string
  confidence: string
  estimated_saving_inr: number | null
  saving_basis: string | null
  evidence_chain: {
    '1_scenario': Record<string, unknown>
    '2_market_signal': Record<string, unknown>
    '3_material_mapping': Record<string, unknown>[]
    '4_purchase_evidence': {
      line_id: string
      po_number: string
      purchase_date: string
      quantity: number
      unit_price_inr: number
      total_value_inr: number
      supplier_name: string
    }[]
    '5_exposure_calculation': Record<string, unknown>
    '6_supplier_alternatives': {
      quote_id: string
      supplier_name: string
      unit_price_inr: number | null
      min_order_qty: number | null
      max_capacity_qty: number | null
      lead_time_days: number | null
      quality_score: number | null
      valid_until: string | null
      feasibility_status: string
      used_as_recommended_alternative: boolean
    }[]
  }
  disclaimer: string
}
