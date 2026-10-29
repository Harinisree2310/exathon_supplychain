import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import DbBanner from '../components/DbBanner'
import { getMaterials, getSupplierComparison } from '../api/supplylens'
import { formatINR } from '../utils/format'
import clsx from 'clsx'

const FEASIBILITY_COLOR: Record<string, string> = {
  FEASIBLE:                'text-green-700 bg-green-100',
  MOQ_NOT_MET:             'text-red-700 bg-red-100',
  CAPACITY_EXCEEDED:       'text-red-700 bg-red-100',
  LEAD_TIME_EXCEEDED:      'text-amber-700 bg-amber-100',
  QUALITY_BELOW_THRESHOLD: 'text-amber-700 bg-amber-100',
  QUOTE_EXPIRED:           'text-gray-600 bg-gray-100',
  PRICE_UNKNOWN:           'text-gray-600 bg-gray-100',
}

export default function SupplierComparison() {
  const [selectedMat, setSelectedMat] = useState('')
  const [requiredQty, setRequiredQty] = useState(1000)
  const [maxLeadTime, setMaxLeadTime] = useState(30)
  const [minQuality, setMinQuality] = useState(6)

  const { data: materials } = useQuery({ queryKey: ['materials'], queryFn: getMaterials })

  const { data: quotes, error, isLoading } = useQuery({
    queryKey: ['supplier-comparison', selectedMat, requiredQty, maxLeadTime, minQuality],
    queryFn: () => getSupplierComparison(selectedMat, {
      required_qty: requiredQty,
      max_lead_time: maxLeadTime,
      min_quality: minQuality,
    }),
    enabled: !!selectedMat,
  })

  const feasible = quotes?.filter((q) => q.feasibility_status === 'FEASIBLE') ?? []
  const infeasible = quotes?.filter((q) => q.feasibility_status !== 'FEASIBLE') ?? []

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <DbBanner error={error} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Supplier Comparison</h1>
        <p className="text-sm text-gray-500 mt-1">
          Compare alternative suppliers for a material. Hard constraint violations are shown explicitly.
        </p>
      </div>

      {/* Filters */}
      <div className="card mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Material</label>
          <select
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
            value={selectedMat}
            onChange={(e) => setSelectedMat(e.target.value)}
          >
            <option value="">Select material…</option>
            {materials?.map((m) => (
              <option key={m.material_id} value={m.material_id}>{m.material_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Required Qty</label>
          <input type="number" min={1}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-28"
            value={requiredQty}
            onChange={(e) => setRequiredQty(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Max Lead Time (days)</label>
          <input type="number" min={1}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-24"
            value={maxLeadTime}
            onChange={(e) => setMaxLeadTime(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Min Quality (0–10)</label>
          <input type="number" min={0} max={10} step={0.5}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-24"
            value={minQuality}
            onChange={(e) => setMinQuality(Number(e.target.value))}
          />
        </div>
      </div>

      {!selectedMat ? (
        <div className="card text-center text-gray-400 py-12">Select a material to compare suppliers.</div>
      ) : isLoading ? (
        <div className="card text-center text-gray-400 py-12">Loading…</div>
      ) : (
        <>
          {/* Feasible */}
          <div className="card mb-4">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <h2 className="font-semibold text-gray-900">
                Feasible Alternatives ({feasible.length})
              </h2>
            </div>
            {feasible.length ? (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase border-b">
                    <th className="pb-2 text-left">Supplier</th>
                    <th className="pb-2 text-right">Unit Price (INR)</th>
                    <th className="pb-2 text-right">MOQ</th>
                    <th className="pb-2 text-right">Capacity</th>
                    <th className="pb-2 text-right">Lead Time</th>
                    <th className="pb-2 text-right">Quality</th>
                    <th className="pb-2 text-center">Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {feasible.map((q) => (
                    <tr key={q.quote_id} className={q.price_rank === 1 ? 'bg-green-50' : ''}>
                      <td className="py-2 font-medium">{q.supplier_name}</td>
                      <td className="py-2 text-right">{formatINR(q.unit_price_inr)}</td>
                      <td className="py-2 text-right">{q.min_order_qty?.toLocaleString() ?? '—'}</td>
                      <td className="py-2 text-right">{q.max_capacity_qty?.toLocaleString() ?? '—'}</td>
                      <td className="py-2 text-right">{q.lead_time_days} days</td>
                      <td className="py-2 text-right">{q.quality_score?.toFixed(1) ?? '—'}</td>
                      <td className="py-2 text-center">
                        {q.price_rank === 1 && (
                          <span className="badge-low">Best Price</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-amber-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                No feasible alternatives for this material with current constraints.
              </p>
            )}
          </div>

          {/* Infeasible */}
          {infeasible.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <XCircle className="w-5 h-5 text-red-500" />
                <h2 className="font-semibold text-gray-900">
                  Rejected Alternatives ({infeasible.length})
                </h2>
              </div>
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase border-b">
                    <th className="pb-2 text-left">Supplier</th>
                    <th className="pb-2 text-right">Unit Price</th>
                    <th className="pb-2 text-left">Rejection Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {infeasible.map((q) => (
                    <tr key={q.quote_id}>
                      <td className="py-2 font-medium">{q.supplier_name}</td>
                      <td className="py-2 text-right">{formatINR(q.unit_price_inr)}</td>
                      <td className="py-2">
                        <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', FEASIBILITY_COLOR[q.feasibility_status] ?? 'bg-gray-100')}>
                          {q.feasibility_status.replace(/_/g, ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
