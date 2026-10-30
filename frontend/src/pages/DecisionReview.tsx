import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Clock, User } from 'lucide-react'
import toast from 'react-hot-toast'
import DbBanner from '../components/DbBanner'
import { listRecommendations, recordDecision, generateRecommendation, listScenarios } from '../api/supplylens'
import { formatINR, actionLabel, actionClass } from '../utils/format'
import { getErrorMessage } from '../utils/errors'
import clsx from 'clsx'

export default function DecisionReview() {
  const qc = useQueryClient()
  const [selectedRec, setSelectedRec] = useState('')
  const [decidedBy, setDecidedBy] = useState('')
  const [notes, setNotes] = useState('')
  const [selectedScenario, setSelectedScenario] = useState('')
  const [selectedMat, setSelectedMat] = useState('')

  const { data: scenarios } = useQuery({ queryKey: ['scenarios'], queryFn: listScenarios })
  const { data: recommendations, error } = useQuery({
    queryKey: ['recommendations', selectedScenario],
    queryFn: () => listRecommendations(selectedScenario || undefined),
  })

  const recMutation = useMutation({
    mutationFn: () => generateRecommendation(selectedScenario, selectedMat),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['recommendations'] })
      toast.success('Recommendation generated')
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  })

  const decisionMutation = useMutation({
    mutationFn: (decision: 'APPROVED' | 'REJECTED' | 'DEFERRED') =>
      recordDecision({ recommendation_id: selectedRec, decision, decided_by: decidedBy, decision_notes: notes }),
    onSuccess: (_, decision) => {
      toast.success(`Decision recorded: ${decision}`)
      setSelectedRec('')
      setNotes('')
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  })

  const selected = recommendations?.find((r) => r.recommendation_id === selectedRec)

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <DbBanner error={error} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Decision Review</h1>
        <p className="text-sm text-gray-500 mt-1">
          Approve, reject or defer a recommended procurement action. Every decision is recorded.
        </p>
      </div>

      {/* Generate recommendation */}
      <div className="card mb-6">
        <h2 className="font-semibold text-gray-900 mb-3">Generate New Recommendation</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">Scenario</label>
            <select
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
            >
              <option value="">Select scenario…</option>
              {scenarios?.map((s) => <option key={s.scenario_id} value={s.scenario_id}>{s.scenario_name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">Material ID</label>
            <input
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
              placeholder="e.g. M001"
              value={selectedMat}
              onChange={(e) => setSelectedMat(e.target.value)}
            />
          </div>
          <button
            className="btn-primary"
            onClick={() => recMutation.mutate()}
            disabled={!selectedScenario || !selectedMat || recMutation.isPending}
          >
            Generate
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recommendation list */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-3">
            Pending Recommendations ({recommendations?.length ?? 0})
          </h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {recommendations?.map((r) => (
              <div
                key={r.recommendation_id}
                onClick={() => setSelectedRec(r.recommendation_id)}
                className={clsx(
                  'p-3 rounded-lg border cursor-pointer transition-colors',
                  selectedRec === r.recommendation_id
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-gray-200 hover:bg-gray-50',
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{r.material_id}</span>
                  <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', actionClass(r.action_code))}>
                    {actionLabel(r.action_code)}
                  </span>
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{r.action_summary}</p>
                {r.estimated_saving_inr && (
                  <p className="text-xs text-green-700 mt-1">
                    Potential saving: {formatINR(r.estimated_saving_inr, true)}
                  </p>
                )}
              </div>
            ))}
            {!recommendations?.length && (
              <p className="text-gray-400 text-sm">No recommendations found.</p>
            )}
          </div>
        </div>

        {/* Decision panel */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-3">Record Decision</h2>
          {selected ? (
            <div className="space-y-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium">{actionLabel(selected.action_code)}</p>
                <p className="text-sm text-gray-600 mt-1">{selected.action_summary}</p>
                {selected.requires_human_review && (
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <User className="w-3 h-3" /> Human review required
                  </p>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">
                  Your Name / Team *
                </label>
                <input
                  className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  placeholder="e.g. Procurement Manager"
                  value={decidedBy}
                  onChange={(e) => setDecidedBy(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">
                  Decision Notes
                </label>
                <textarea
                  rows={3}
                  className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5"
                  placeholder="Optional: rationale, conditions, follow-up actions…"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div className="flex gap-3">
                <button
                  className="btn-primary flex-1 justify-center"
                  onClick={() => decisionMutation.mutate('APPROVED')}
                  disabled={!decidedBy || decisionMutation.isPending}
                >
                  <CheckCircle className="w-4 h-4" /> Approve
                </button>
                <button
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  onClick={() => decisionMutation.mutate('REJECTED')}
                  disabled={!decidedBy || decisionMutation.isPending}
                >
                  <XCircle className="w-4 h-4" /> Reject
                </button>
                <button
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors disabled:opacity-50"
                  onClick={() => decisionMutation.mutate('DEFERRED')}
                  disabled={!decidedBy || decisionMutation.isPending}
                >
                  <Clock className="w-4 h-4" /> Defer
                </button>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Select a recommendation to review.</p>
          )}
        </div>
      </div>
    </div>
  )
}
