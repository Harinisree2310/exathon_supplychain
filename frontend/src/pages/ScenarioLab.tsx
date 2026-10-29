import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { FlaskConical, Play, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import DbBanner from '../components/DbBanner'
import {
  createScenario, listScenarios, calculateScenario, getExposureResults,
} from '../api/supplylens'
import { formatINR, formatPct } from '../utils/format'

const COMMODITIES = [
  { code: 'BRENT_CRUDE',   label: 'Brent Crude Oil' },
  { code: 'LME_COPPER',    label: 'LME Copper' },
  { code: 'LME_HRC_STEEL', label: 'LME Hot-Rolled Steel' },
  { code: 'NAPHTHA_SPOT',  label: 'Naphtha Spot' },
  { code: 'LME_ALUMINIUM', label: 'LME Aluminium' },
  { code: 'PALM_OIL_BMD',  label: 'Palm Oil BMD' },
  { code: 'COKING_COAL',   label: 'Coking Coal' },
]

export default function ScenarioLab() {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    scenario_name: 'Brent Crude +15% Shock',
    commodity_code: 'BRENT_CRUDE',
    shock_pct: 15,
    shock_direction: 'UP' as 'UP' | 'DOWN',
    analysis_period_start: '2025-07-01',
    analysis_period_end: '2026-01-01',
  })
  const [activeScenario, setActiveScenario] = useState<string | null>(null)

  const { data: scenarios, error } = useQuery({
    queryKey: ['scenarios'],
    queryFn: listScenarios,
  })
  const { data: exposures } = useQuery({
    queryKey: ['exposures', activeScenario],
    queryFn: () => getExposureResults(activeScenario!),
    enabled: !!activeScenario,
  })

  const createMutation = useMutation({
    mutationFn: createScenario,
    onSuccess: (sc) => {
      qc.invalidateQueries({ queryKey: ['scenarios'] })
      setActiveScenario(sc.scenario_id)
      toast.success('Scenario created')
    },
  })

  const calcMutation = useMutation({
    mutationFn: (sid: string) => calculateScenario(sid),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['exposures'] })
      toast.success(`Calculated: ${data.length} material exposures`)
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? e.message),
  })

  const totalIncremental = exposures?.reduce(
    (s, e) => s + Number(e.incremental_cost_inr), 0
  ) ?? 0

  const chartData = exposures?.map((e) => ({
    name: e.material_name.split(' ').slice(0, 2).join(' '),
    observed: Number(e.observed_spend_inr) / 1_00_000,
    exposed: Number(e.exposed_spend_inr) / 1_00_000,
    incremental: Number(e.incremental_cost_inr) / 1_00_000,
  })) ?? []

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <DbBanner error={error} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Scenario Lab</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure a hypothetical commodity shock and see the estimated impact on procurement cost.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenario form */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical className="w-5 h-5 text-brand-600" />
            <h2 className="font-semibold text-gray-900">New Scenario</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Name</label>
              <input
                className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                value={form.scenario_name}
                onChange={(e) => setForm({ ...form, scenario_name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Commodity</label>
              <select
                className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                value={form.commodity_code}
                onChange={(e) => setForm({ ...form, commodity_code: e.target.value })}
              >
                {COMMODITIES.map((c) => (
                  <option key={c.code} value={c.code}>{c.label}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Shock %</label>
                <input
                  type="number" min={0} max={100} step={0.5}
                  className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  value={form.shock_pct}
                  onChange={(e) => setForm({ ...form, shock_pct: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Direction</label>
                <select
                  className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  value={form.shock_direction}
                  onChange={(e) => setForm({ ...form, shock_direction: e.target.value as 'UP' | 'DOWN' })}
                >
                  <option value="UP">UP ↑</option>
                  <option value="DOWN">DOWN ↓</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600">From</label>
                <input type="date"
                  className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  value={form.analysis_period_start}
                  onChange={(e) => setForm({ ...form, analysis_period_start: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">To</label>
                <input type="date"
                  className="mt-1 w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  value={form.analysis_period_end}
                  onChange={(e) => setForm({ ...form, analysis_period_end: e.target.value })}
                />
              </div>
            </div>
            <button
              className="btn-primary w-full justify-center"
              onClick={() => createMutation.mutate(form)}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
              Create Scenario
            </button>
          </div>
        </div>

        {/* Scenario list */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-3">Saved Scenarios</h2>
          {scenarios?.length ? (
            <div className="space-y-2">
              {scenarios.map((sc) => (
                <div
                  key={sc.scenario_id}
                  onClick={() => setActiveScenario(sc.scenario_id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    activeScenario === sc.scenario_id
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <p className="text-sm font-medium">{sc.scenario_name}</p>
                  <p className="text-xs text-gray-500">
                    {sc.commodity_code} {sc.shock_direction} {sc.shock_pct}%
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No scenarios yet.</p>
          )}

          {activeScenario && (
            <button
              className="btn-primary mt-4 w-full justify-center"
              onClick={() => calcMutation.mutate(activeScenario)}
              disabled={calcMutation.isPending}
            >
              {calcMutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run Calculation
            </button>
          )}
        </div>

        {/* Summary */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-3">Impact Summary</h2>
          {exposures?.length ? (
            <>
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-xs text-red-600 font-medium">Total Incremental Cost</p>
                <p className="text-2xl font-bold text-red-700 mt-0.5">
                  {formatINR(totalIncremental, true)}
                </p>
                <p className="text-xs text-red-500 mt-1">Hypothetical — not a forecast</p>
              </div>
              <div className="space-y-2">
                {exposures.map((e) => (
                  <div key={e.material_id} className="flex justify-between text-sm">
                    <span className="text-gray-700 truncate max-w-[150px]">{e.material_name}</span>
                    <span className="font-medium text-red-600">
                      +{formatINR(Number(e.incremental_cost_inr), true)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-gray-400 text-sm">
              Select a scenario and click Run Calculation to see results.
            </p>
          )}
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="card mt-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Baseline vs Shocked Cost by Material (₹ Lakhs)
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [`₹${v.toFixed(1)}L`]} />
              <Legend />
              <Bar dataKey="observed" fill="#93c5fd" name="Observed Spend" />
              <Bar dataKey="exposed" fill="#3b82f6" name="Exposed Spend" />
              <Bar dataKey="incremental" fill="#ef4444" name="Incremental Cost" />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-400 mt-2">
            Incremental cost = exposed spend × shock %. All figures synthetic.
          </p>
        </div>
      )}
    </div>
  )
}
