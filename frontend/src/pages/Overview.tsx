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

      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-semibold tracking-[0.18em] text-brand-700">SUPPLY CHAIN INTELLIGENCE</p>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900 sm:text-[28px]">Procurement overview</h1>
          <p className="mt-1.5 text-sm text-gray-500">
            A clear view of spend, material exposure and supplier concentration.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-brand-500" />
          6-month snapshot
        </div>
      </div>

      {/* KPI Cards */}
      <div className="mb-7 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total procurement spend"
          value={formatINR(stats?.total_purchase_spend_inr, true)}
          sub="Across the reporting period"
          icon={<DollarSign className="h-[19px] w-[19px]" />}
          loading={isLoading}
        />
        <StatCard
          label="Exposed materials"
          value={stats?.exposed_material_count ?? '—'}
          sub="With commodity mapping"
          icon={<TrendingUp className="h-[19px] w-[19px]" />}
          loading={isLoading}
        />
        <StatCard
          label="High-concentration materials"
          value={stats?.high_concentration_materials ?? '—'}
          sub="HHI above 2,500"
          variant={stats?.high_concentration_materials ? 'warning' : 'default'}
          icon={<AlertTriangle className="h-[19px] w-[19px]" />}
          loading={isLoading}
        />
        <StatCard
          label="Registered suppliers"
          value={stats?.supplier_count ?? '—'}
          sub="In your supplier network"
          icon={<Users className="h-[19px] w-[19px]" />}
          loading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        {/* Monthly Spend Chart */}
        <div className="card">
          <div className="mb-5">
            <p className="text-[10px] font-semibold tracking-[0.14em] text-gray-400">SPEND TREND</p>
            <h2 className="mt-1 text-[15px] font-semibold text-gray-800">Monthly procurement spend</h2>
          </div>
          {spendHistory?.history?.length ? (
            <ResponsiveContainer width="100%" height={236}>
              <BarChart data={spendHistory.history}>
                <CartesianGrid vertical={false} strokeDasharray="3 5" stroke="#e9eef0" />
                <XAxis
                  dataKey="month"
                  tickFormatter={(v) => v.slice(0, 7)}
                  tick={{ fontSize: 11, fill: '#81909a' }}
                  axisLine={false}
                  tickLine={false}
                  dy={8}
                />
                <YAxis
                  tickFormatter={(v) => `₹${(v / 1_00_000).toFixed(0)}L`}
                  tick={{ fontSize: 11, fill: '#81909a' }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />
                <Tooltip
                  formatter={(v: number) => [formatINR(v, true), 'Spend']}
                  labelFormatter={(l) => l.slice(0, 7)}
                  contentStyle={{ borderRadius: 10, borderColor: '#e5ebef', boxShadow: '0 8px 24px rgba(24,43,58,.10)' }}
                />
                <Bar dataKey="spend_inr" fill="#2b8278" radius={[5, 5, 0, 0]} maxBarSize={38} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[236px] flex-col items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/60 px-5 text-center">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-gray-400 shadow-sm">
                <DollarSign className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium text-gray-700">Your spend trend will appear here</p>
              <p className="mt-1 max-w-xs text-xs leading-5 text-gray-500">
                Load procurement data in Data Workspace to start exploring spend over time.
              </p>
            </div>
          )}
        </div>

        {/* Concentration Table */}
        <div className="card">
          <div className="mb-5">
            <p className="text-[10px] font-semibold tracking-[0.14em] text-gray-400">SUPPLIER EXPOSURE</p>
            <h2 className="mt-1 text-[15px] font-semibold text-gray-800">
              Concentration by material <span className="font-normal text-gray-400">· HHI index</span>
            </h2>
          </div>
          {concentration?.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase border-b">
                    <th className="pb-3 text-left font-medium">Material</th>
                    <th className="pb-3 text-right font-medium">HHI</th>
                    <th className="pb-3 text-right font-medium">Dominant %</th>
                    <th className="pb-3 text-center font-medium">Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {concentration.map((c) => (
                    <tr key={c.material_id} className="hover:bg-gray-50/80">
                      <td className="max-w-[160px] truncate py-3 font-medium text-gray-800">
                        {c.material_name}
                      </td>
                      <td className="py-3 text-right tabular-nums text-gray-700">{Number(c.hhi).toFixed(0)}</td>
                      <td className="py-3 text-right tabular-nums text-gray-700">
                        {formatPct(c.dominant_share_pct)}
                      </td>
                      <td className="py-3 text-center">
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
            <div className="flex h-[236px] flex-col items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/60 px-5 text-center">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-gray-400 shadow-sm">
                <Users className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium text-gray-700">No supplier concentration yet</p>
              <p className="mt-1 max-w-xs text-xs leading-5 text-gray-500">
                Concentration insights show how supplier dependence is distributed across materials.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Data quality notice */}
      <div className="mt-6 flex items-start gap-2.5 rounded-lg border border-gray-200/80 bg-white/70 px-4 py-3 text-xs leading-5 text-gray-500">
        <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />
        <p>
          Demo insights use synthetic data only. Analytics are powered by Exasol Personal; no real commercial data is shown.
        </p>
      </div>
    </div>
  )
}
