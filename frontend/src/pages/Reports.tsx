import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileDown, FileJson, FileSpreadsheet } from 'lucide-react'
import toast from 'react-hot-toast'
import DbBanner from '../components/DbBanner'
import { listScenarios, exportReport } from '../api/supplylens'

export default function Reports() {
  const [selectedScenario, setSelectedScenario] = useState('')
  const [exporting, setExporting] = useState(false)

  const { data: scenarios, error } = useQuery({
    queryKey: ['scenarios'],
    queryFn: listScenarios,
  })

  const handleExport = async (fmt: 'json' | 'csv') => {
    if (!selectedScenario) {
      toast.error('Select a scenario first')
      return
    }
    setExporting(true)
    try {
      const blob = await exportReport(selectedScenario, fmt)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `supplylens-report-${selectedScenario}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Report downloaded as ${fmt.toUpperCase()}`)
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? e.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <DbBanner error={error} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Reports</h1>
        <p className="text-sm text-gray-500 mt-1">
          Export the full JSON report or a compact CSV exposure summary.
        </p>
      </div>

      <div className="card">
        <div className="mb-6">
          <label className="text-xs font-medium text-gray-600 block mb-2">Select Scenario</label>
          <select
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-full max-w-md"
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
          >
            <option value="">Choose a scenario…</option>
            {scenarios?.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.scenario_name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-4">
          <button
            className="btn-primary"
            onClick={() => handleExport('json')}
            disabled={!selectedScenario || exporting}
          >
            <FileJson className="w-4 h-4" />
            Export JSON Report
          </button>
          <button
            className="btn-secondary"
            onClick={() => handleExport('csv')}
            disabled={!selectedScenario || exporting}
          >
            <FileSpreadsheet className="w-4 h-4" />
            Export CSV Report
          </button>
        </div>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-700 mb-2">JSON report includes:</p>
          <ul className="text-sm text-gray-600 space-y-1">
            {[
              'Scenario configuration and analysis period',
              'Methodology: formulas for observed spend, exposed spend, incremental cost, HHI',
              'Exposure results by material with commodity weights',
              'Recommendations with confidence levels',
              'Recommendation evidence summaries and saving basis',
              'Recorded decisions, notes and timestamps',
              'Data limitations and disclaimer',
            ].map((item) => (
              <li key={item} className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                {item}
              </li>
            ))}
          </ul>
          <p className="text-xs text-gray-500 mt-3">
            CSV contains scenario metadata and material exposure results only.
          </p>
        </div>

        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          All data in this report is synthetic. No real commercial information is included.
          Reports are for demonstration purposes only.
        </div>
      </div>
    </div>
  )
}
