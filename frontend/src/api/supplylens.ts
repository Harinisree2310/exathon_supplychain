import { api } from './client'
import type {
  ConcentrationResult,
  DataQuality,
  EvidenceTrace,
  ExposureResult,
  HealthStatus,
  MarketSignal,
  Material,
  OverviewStats,
  PurchaseUploadResult,
  Recommendation,
  Scenario,
  SpendHistory,
  Supplier,
  SupplierQuote,
} from '../types'

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () =>
  api.get<HealthStatus>('/health').then((r) => r.data)

// ── Data Workspace ────────────────────────────────────────────────────────────
export const loadDemoData = (force = false) =>
  api.post(`/api/v1/data/load-demo?force=${force}`).then((r) => r.data)

export const getDataQuality = () =>
  api.get<DataQuality>('/api/v1/data/quality').then((r) => r.data)

export const uploadPurchases = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<PurchaseUploadResult>('/api/v1/data/upload/purchases', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getMaterials = () =>
  api.get<Material[]>('/api/v1/analytics/materials').then((r) => r.data)

export const getSuppliers = () =>
  api.get<Supplier[]>('/api/v1/analytics/suppliers').then((r) => r.data)

export const getMarketSignals = (commodityCode?: string, limit = 180) =>
  api
    .get<MarketSignal[]>('/api/v1/analytics/market-signals', {
      params: { commodity_code: commodityCode, limit },
    })
    .then((r) => r.data)

export const getConcentration = () =>
  api.get<ConcentrationResult[]>('/api/v1/analytics/concentration').then((r) => r.data)

export const getOverview = () =>
  api.get<OverviewStats>('/api/v1/analytics/overview').then((r) => r.data)

export const getSpendHistory = (materialId?: string) =>
  api
    .get<SpendHistory>('/api/v1/analytics/spend-history', {
      params: { material_id: materialId },
    })
    .then((r) => r.data)

// ── Scenarios ─────────────────────────────────────────────────────────────────
export const createScenario = (payload: {
  scenario_name: string
  commodity_code: string
  shock_pct: number
  shock_direction: 'UP' | 'DOWN'
  analysis_period_start: string
  analysis_period_end: string
}) => api.post<Scenario>('/api/v1/analytics/scenarios', payload).then((r) => r.data)

export const listScenarios = () =>
  api.get<Scenario[]>('/api/v1/analytics/scenarios').then((r) => r.data)

export const calculateScenario = (scenarioId: string) =>
  api
    .post<ExposureResult[]>(`/api/v1/analytics/scenarios/${scenarioId}/calculate`)
    .then((r) => r.data)

export const getExposureResults = (scenarioId: string) =>
  api
    .get<ExposureResult[]>(`/api/v1/analytics/scenarios/${scenarioId}/results`)
    .then((r) => r.data)

// ── Supplier Comparison ───────────────────────────────────────────────────────
export const getSupplierComparison = (
  materialId: string,
  params: { required_qty?: number; max_lead_time?: number; min_quality?: number } = {},
) =>
  api
    .get<SupplierQuote[]>(`/api/v1/analytics/supplier-comparison/${materialId}`, { params })
    .then((r) => r.data)

// ── Recommendations ───────────────────────────────────────────────────────────
export const generateRecommendation = (
  scenarioId: string,
  materialId: string,
  params: { required_qty?: number; max_lead_time?: number; min_quality?: number } = {},
) =>
  api
    .post<Recommendation>('/api/v1/analytics/recommendations', null, {
      params: { scenario_id: scenarioId, material_id: materialId, ...params },
    })
    .then((r) => r.data)

export const listRecommendations = (scenarioId?: string) =>
  api
    .get<Recommendation[]>('/api/v1/analytics/recommendations', {
      params: { scenario_id: scenarioId },
    })
    .then((r) => r.data)

// ── Evidence ──────────────────────────────────────────────────────────────────
export const getEvidenceTrace = (recommendationId: string) =>
  api
    .get<EvidenceTrace>(`/api/v1/analytics/evidence/${recommendationId}`)
    .then((r) => r.data)

// ── Decisions ─────────────────────────────────────────────────────────────────
export const recordDecision = (payload: {
  recommendation_id: string
  decision: 'APPROVED' | 'REJECTED' | 'DEFERRED'
  decided_by: string
  decision_notes?: string
}) =>
  api.post('/api/v1/analytics/decisions', payload).then((r) => r.data)

// ── Reports ───────────────────────────────────────────────────────────────────
export const exportReport = (scenarioId: string, fmt: 'json' | 'csv' = 'json') =>
  api
    .get(`/api/v1/reports/export/${scenarioId}`, {
      params: { fmt },
      responseType: 'blob',
    })
    .then((r) => r.data)
