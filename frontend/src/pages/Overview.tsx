import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import {
  DollarSign, AlertTriangle, Users, TrendingUp,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import DbBanner from '../components/DbBanner'
import { getOverview, getSpendHistory, getConcentration } from '../api/supplylens'
import { formatINR, formatPct, concentrationClass } from '../utils/format'

export default function Overview() {
  const { data: stats, error: statsErr, isLoading } = useQuery({
    queryKey: ['overview'],
    queryFn: getOverview,
  })
  const { data: spendHistory } = useQuery({
    queryKey: ['spend-history'],
    queryFn: () => getSpendHistory(),
  })
  const { data: concentration } = useQuery({
    queryKey: ['concentration'],
    queryFn: getConcentration,
  })

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <DbBanner error={statsErr} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Overview</h1>
        <p className="text-sm text-gray-500 mt-1">
          Procurement spend, material risk exposure and supplier concentration.
          Source: Exasol Personal.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Procurement Spend"
          value={formatINR(stats?.total_purchase_spend_inr, true)}
          sub="6-month period"
          icon={<DollarSign className="w-6 h-6" />}
          loading={isLoading}
        />
        <StatCard
          label="Exposed Materials"
          value={stats?.exposed_material_count ?? '—'}
          sub="with commodity mapping"
          icon={<TrendingUp className="w-6 h-6" />}
          loading={isLoading}
        />
        <StatCard
          label="High-Concentration Materials"
          value={stats?.high_concentration_materials ?? '—'}
          sub="HHI > 2500"
          variant={stats?.high_concentration_materials ? 'warning' : 'default'}
          icon={<AlertTriangle className="w-6 h-6" />}
          loading={isLoading}
        />
        <StatCard
          label="Registered Suppliers"
          value={stats?.supplier_count ?? '—'}
          icon={<Users className="w-6 h-6" />}
          loading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Spend Chart */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Monthly Procurement Spend</h2>
          {spendHistory?.history?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={spendHistory.history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="month"
                  tickFormatter={(v) => v.slice(0, 7)}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  tickFormatter={(v) => `₹${(v / 1_00_000).toFixed(0)}L`}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v: number) => [formatINR(v, true), 'Spend']}
                  labelFormatter={(l) => l.slice(0, 7)}
                />
                <Bar dataKey="spend_inr" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">
              No spend data loaded yet — use Data Workspace to load demo data.
            </div>
          )}
        </div>

        {/* Concentration Table */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Supplier Concentration by Material
            <span className="ml-2 text-xs font-normal text-gray-400">(HHI index)</span>
          </h2>
          {concentration?.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase border-b">
                    <th className="pb-2 text-left font-medium">Material</th>
                    <th className="pb-2 text-right font-medium">HHI</th>
                    <th className="pb-2 text-right font-medium">Dominant%</th>
                    <th className="pb-2 text-center font-medium">Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {concentration.map((c) => (
                    <tr key={c.material_id} className="hover:bg-gray-50">
                      <td className="py-2 text-gray-900 font-medium truncate max-w-[160px]">
                        {c.material_name}
                      </td>
                      <td className="py-2 text-right text-gray-700">{c.hhi.toFixed(0)}</td>
                      <td className="py-2 text-right text-gray-700">
                        {formatPct(c.dominant_share_pct)}
                      </td>
                      <td className="py-2 text-center">
                        <span className={concentrationClass(c.concentration_level)}>
                          {c.concentration_level}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No concentration data yet.</p>
          )}
        </div>
      </div>

      {/* Data quality notice */}
      <p className="mt-6 text-xs text-gray-400">
        All figures are derived from the synthetic dataset. No real commercial data.
        Powered by Exasol Personal analytics.
      </p>
    </div>
  )
}
