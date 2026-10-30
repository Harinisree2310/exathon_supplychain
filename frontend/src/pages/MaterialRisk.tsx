import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import DbBanner from '../components/DbBanner'
import { getMaterials, getMarketSignals, getSpendHistory, getConcentration } from '../api/supplylens'
import { formatINR, concentrationClass } from '../utils/format'

export default function MaterialRisk() {
  const [selectedMat, setSelectedMat] = useState('')
  const [selectedCommodity, setSelectedCommodity] = useState('BRENT_CRUDE')

  const { data: materials, error: matErr } = useQuery({
    queryKey: ['materials'],
    queryFn: getMaterials,
  })
  const { data: signals } = useQuery({
    queryKey: ['signals', selectedCommodity],
    queryFn: () => getMarketSignals(selectedCommodity, 180),
    enabled: !!selectedCommodity,
  })
  const { data: spendHist } = useQuery({
    queryKey: ['spend-history', selectedMat],
    queryFn: () => getSpendHistory(selectedMat || undefined),
    enabled: true,
  })
  const { data: concentration } = useQuery({
    queryKey: ['concentration'],
    queryFn: getConcentration,
  })

  const matConc = concentration?.find((c) => c.material_id === selectedMat)

  const COMMODITIES = [
    'BRENT_CRUDE', 'LME_COPPER', 'LME_HRC_STEEL',
    'NAPHTHA_SPOT', 'LME_ALUMINIUM', 'PALM_OIL_BMD', 'COKING_COAL',
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <DbBanner error={matErr} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Material Risk Explorer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Historical purchase spend, commodity price signals and exposure evidence.
        </p>
      </div>

      {/* Filters */}
      <div className="card mb-6 flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Material</label>
          <select
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white"
            value={selectedMat}
            onChange={(e) => setSelectedMat(e.target.value)}
          >
            <option value="">All materials</option>
            {materials?.map((m) => (
              <option key={m.material_id} value={m.material_id}>{m.material_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Commodity Signal</label>
          <select
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white"
            value={selectedCommodity}
            onChange={(e) => setSelectedCommodity(e.target.value)}
          >
            {COMMODITIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        {matConc && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-gray-500">Concentration:</span>
            <span className={concentrationClass(matConc.concentration_level)}>
              {matConc.concentration_level} (HHI {Number(matConc.hhi).toFixed(0)})
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spend history */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Monthly Procurement Spend
            {selectedMat && materials && (
              <span className="ml-2 font-normal text-gray-400">
                – {materials.find(m => m.material_id === selectedMat)?.material_name}
              </span>
            )}
          </h2>
          {spendHist?.history?.length ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={spendHist.history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="month" tickFormatter={(v) => v.slice(5, 7) + '/' + v.slice(2, 4)} tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `₹${(v / 1_00_000).toFixed(0)}L`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [formatINR(v, true), 'Spend']} />
                <Line type="monotone" dataKey="spend_inr" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm">Load data to see spend history.</p>
          )}
        </div>

        {/* Market signal */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            {selectedCommodity} Price History
          </h2>
          {signals?.length ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={[...signals].sort((a, b) => a.signal_date.localeCompare(b.signal_date))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="signal_date" tickFormatter={(v) => v.slice(5)} tick={{ fontSize: 11 }} interval={29} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number) => [`${v.toFixed(2)} ${signals[0]?.currency ?? ''}`, 'Price']}
                />
                <Line type="monotone" dataKey="price" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm">No signal data for this commodity.</p>
          )}
          <p className="text-xs text-gray-400 mt-2">
            Source: Synthetic simulation. Not real market data.
          </p>
        </div>
      </div>

      {/* Material table */}
      <div className="card mt-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">All Materials</h2>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 uppercase border-b">
              <th className="pb-2 text-left">Code</th>
              <th className="pb-2 text-left">Name</th>
              <th className="pb-2 text-left">Category</th>
              <th className="pb-2 text-left">UoM</th>
              <th className="pb-2 text-center">Concentration</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {materials?.map((m) => {
              const conc = concentration?.find((c) => c.material_id === m.material_id)
              return (
                <tr
                  key={m.material_id}
                  className={`hover:bg-gray-50 cursor-pointer ${selectedMat === m.material_id ? 'bg-brand-50' : ''}`}
                  onClick={() => setSelectedMat(m.material_id)}
                >
                  <td className="py-2 font-mono text-xs">{m.material_code}</td>
                  <td className="py-2 font-medium">{m.material_name}</td>
                  <td className="py-2 text-gray-500">{m.category}</td>
                  <td className="py-2 text-gray-500">{m.unit_of_measure}</td>
                  <td className="py-2 text-center">
                    {conc ? (
                      <span className={concentrationClass(conc.concentration_level)}>
                        {conc.concentration_level}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
