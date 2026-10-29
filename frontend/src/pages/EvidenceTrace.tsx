import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Search } from 'lucide-react'
import DbBanner from '../components/DbBanner'
import { getEvidenceTrace, listRecommendations } from '../api/supplylens'
import { formatINR, actionLabel, actionClass } from '../utils/format'
import clsx from 'clsx'

function Section({
  title, badge, children, defaultOpen = true,
}: { title: string; badge?: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden mb-3">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-sm font-medium"
        onClick={() => setOpen(!open)}
      >
        <span className="flex items-center gap-2">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {title}
          {badge && <span className="text-xs font-normal text-gray-400">({badge})</span>}
        </span>
      </button>
      {open && <div className="p-4 bg-white">{children}</div>}
    </div>
  )
}

function KV({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex gap-2 text-sm mb-1">
      <span className="text-gray-500 w-44 flex-shrink-0">{label}</span>
      <span className="text-gray-900 font-mono text-xs">{String(value ?? '—')}</span>
    </div>
  )
}

export default function EvidenceTrace() {
  const [selectedRec, setSelectedRec] = useState('')

  const { data: recommendations, error: recErr } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => listRecommendations(),
  })

  const { data: trace, error: traceErr, isLoading } = useQuery({
    queryKey: ['evidence', selectedRec],
    queryFn: () => getEvidenceTrace(selectedRec),
    enabled: !!selectedRec,
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <DbBanner error={recErr || traceErr} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Evidence Trace</h1>
        <p className="text-sm text-gray-500 mt-1">
          Inspect every step that produced a recommendation: market signal → mapping
          → purchases → exposure → suppliers.
        </p>
      </div>

      {/* Select recommendation */}
      <div className="card mb-6">
        <label className="text-xs font-medium text-gray-600 block mb-2">
          <Search className="w-3.5 h-3.5 inline mr-1" />
          Select Recommendation
        </label>
        <select
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-full"
          value={selectedRec}
          onChange={(e) => setSelectedRec(e.target.value)}
        >
          <option value="">Choose a recommendation…</option>
          {recommendations?.map((r) => (
            <option key={r.recommendation_id} value={r.recommendation_id}>
              {r.material_id} — {r.action_code}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading evidence chain…</p>}

      {trace && (
        <div>
          {/* Header */}
          <div className="card mb-4 flex items-start justify-between">
            <div>
              <p className="font-semibold text-gray-900">{trace.material_name}</p>
              <p className="text-sm text-gray-600 mt-1">{trace.action_summary}</p>
              {trace.estimated_saving_inr && (
                <p className="text-xs text-green-700 mt-1">
                  Estimated saving: {formatINR(trace.estimated_saving_inr, true)}
                  <span className="text-gray-400"> — indicative only</span>
                </p>
              )}
            </div>
            <span className={clsx('px-3 py-1 rounded-full text-xs font-medium', actionClass(trace.action_code))}>
              {actionLabel(trace.action_code)}
            </span>
          </div>

          {/* Chain */}
          <Section title="① Scenario" badge="market shock definition">
            {Object.entries(trace.evidence_chain['1_scenario']).map(([k, v]) => (
              <KV key={k} label={k} value={v as string} />
            ))}
          </Section>

          <Section title="② Market Signal" badge="latest price observation">
            {Object.entries(trace.evidence_chain['2_market_signal']).map(([k, v]) => (
              <KV key={k} label={k} value={v as string} />
            ))}
          </Section>

          <Section title="③ Material–Commodity Mapping" badge="exposure weights">
            {trace.evidence_chain['3_material_mapping'].map((m, i) => (
              <div key={i} className="mb-3 p-3 bg-gray-50 rounded-lg text-sm">
                {Object.entries(m).map(([k, v]) => (
                  <KV key={k} label={k} value={v as string} />
                ))}
              </div>
            ))}
          </Section>

          <Section title="④ Purchase Evidence" badge="last 5 purchase lines">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b">
                  <th className="pb-1 text-left">PO</th>
                  <th className="pb-1 text-left">Date</th>
                  <th className="pb-1 text-left">Supplier</th>
                  <th className="pb-1 text-right">Qty</th>
                  <th className="pb-1 text-right">Unit Price</th>
                  <th className="pb-1 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {trace.evidence_chain['4_purchase_evidence'].map((p: any, i) => (
                  <tr key={i}>
                    <td className="py-1 font-mono">{p.po_number}</td>
                    <td className="py-1">{p.purchase_date}</td>
                    <td className="py-1">{p.supplier_name}</td>
                    <td className="py-1 text-right">{Number(p.quantity).toLocaleString()}</td>
                    <td className="py-1 text-right">{formatINR(p.unit_price_inr)}</td>
                    <td className="py-1 text-right">{formatINR(p.total_value_inr, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="⑤ Exposure Calculation">
            {Object.entries(trace.evidence_chain['5_exposure_calculation']).map(([k, v]) => (
              <KV key={k} label={k} value={v as string} />
            ))}
          </Section>

          <Section title="⑥ Supplier Alternatives">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b">
                  <th className="pb-1 text-left">Supplier</th>
                  <th className="pb-1 text-right">Price</th>
                  <th className="pb-1 text-right">MOQ</th>
                  <th className="pb-1 text-right">Capacity</th>
                  <th className="pb-1 text-right">Lead</th>
                  <th className="pb-1 text-right">Quality</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {trace.evidence_chain['6_supplier_alternatives'].map((s: any, i) => (
                  <tr key={i}>
                    <td className="py-1">{s.supplier_name}</td>
                    <td className="py-1 text-right">{s.unit_price_inr ? formatINR(s.unit_price_inr) : '—'}</td>
                    <td className="py-1 text-right">{s.min_order_qty?.toLocaleString() ?? '—'}</td>
                    <td className="py-1 text-right">{s.max_capacity_qty?.toLocaleString() ?? '—'}</td>
                    <td className="py-1 text-right">{s.lead_time_days ?? '—'} d</td>
                    <td className="py-1 text-right">{s.quality_score ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 mt-4">
            ⚠ {trace.disclaimer}
          </p>
        </div>
      )}
    </div>
  )
}
