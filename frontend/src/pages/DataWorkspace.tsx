import React, { useCallback, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { Database, Upload, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import DbBanner from '../components/DbBanner'
import { getDataQuality, loadDemoData, uploadPurchases } from '../api/supplylens'
import { getErrorMessage } from '../utils/errors'
import type { PurchaseUploadResult } from '../types'

export default function DataWorkspace() {
  const qc = useQueryClient()
  const [uploadResult, setUploadResult] = useState<PurchaseUploadResult | null>(null)

  const { data: quality, error: qErr, isLoading } = useQuery({
    queryKey: ['quality'],
    queryFn: getDataQuality,
  })

  const loadDemoMutation = useMutation({
    mutationFn: (force: boolean) => loadDemoData(force),
    onSuccess: () => {
      toast.success('Demo data loaded successfully')
      qc.invalidateQueries()
    },
    onError: (error: unknown) => toast.error(`Failed to load demo data: ${getErrorMessage(error)}`),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadPurchases(file),
    onSuccess: (data) => {
      setUploadResult(data)
      qc.invalidateQueries()
      if (data.success) toast.success(`Ingested: ${data.data?.accepted} rows accepted`)
      else toast.error(`Upload issue: ${data.message}`)
    },
    onError: (error: unknown) => toast.error(`Upload failed: ${getErrorMessage(error)}`),
  })

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) uploadMutation.mutate(files[0])
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.xls', '.xlsx'],
               'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxFiles: 1,
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <DbBanner error={qErr} />

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Data Workspace</h1>
        <p className="text-sm text-gray-500 mt-1">
          Load the demo dataset or upload your own purchase CSV/Excel files.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Load Demo */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center">
              <Database className="w-4 h-4 text-brand-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Demo Dataset</h2>
              <p className="text-xs text-gray-500">Seed=42 synthetic data</p>
            </div>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Loads 7 suppliers, 6 materials, 6 months of purchase history and
            synthetic market signals into Exasol.
          </p>
          <div className="flex gap-3">
            <button
              className="btn-primary"
              onClick={() => loadDemoMutation.mutate(false)}
              disabled={loadDemoMutation.isPending}
            >
              {loadDemoMutation.isPending ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Database className="w-4 h-4" />
              )}
              Load Demo Data
            </button>
            <button
              className="btn-secondary"
              onClick={() => loadDemoMutation.mutate(true)}
              disabled={loadDemoMutation.isPending}
            >
              Reset & Reload
            </button>
          </div>
        </div>

        {/* Upload */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
              <Upload className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Upload Purchase File</h2>
              <p className="text-xs text-gray-500">CSV or Excel</p>
            </div>
          </div>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600">
              {isDragActive ? 'Drop file here' : 'Drag & drop or click to select'}
            </p>
            <p className="text-xs text-gray-400 mt-1">CSV or Excel, max 10 MB</p>
          </div>

          {uploadMutation.isPending && (
            <p className="text-sm text-gray-600 mt-3 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" /> Processing…
            </p>
          )}

          {uploadResult && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm">
              <div className="flex items-center gap-2 mb-2">
                {uploadResult.success
                  ? <CheckCircle className="w-4 h-4 text-green-600" />
                  : <AlertTriangle className="w-4 h-4 text-amber-600" />}
                <span className="font-medium">{uploadResult.message}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                <div>Accepted: <strong>{uploadResult.data?.accepted}</strong></div>
                <div>Rejected: <strong>{uploadResult.data?.rejected}</strong></div>
                <div>Duplicates: <strong>{uploadResult.data?.duplicates}</strong></div>
              </div>
            </div>
          )}

          <a
            href="/api/v1/data/template/purchases"
            className="text-xs text-brand-600 hover:underline mt-3 inline-block"
          >
            Download purchase CSV template
          </a>
        </div>
      </div>

      {/* Data Quality */}
      <div className="card mt-6">
        <h2 className="font-semibold text-gray-900 mb-4">Data Quality Summary</h2>
        {isLoading ? (
          <div className="h-20 flex items-center justify-center text-gray-400 text-sm">
            Loading…
          </div>
        ) : quality ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Materials',       value: quality.total_materials },
              { label: 'Suppliers',        value: quality.total_suppliers },
              { label: 'Purchase Lines',   value: quality.total_purchase_lines },
              { label: 'Market Signals',   value: quality.total_market_signals },
              { label: 'Mapped Materials', value: quality.materials_with_mapping, ok: true },
              { label: 'Unmapped',         value: quality.materials_without_mapping, warn: quality.materials_without_mapping > 0 },
              { label: 'Stale Signals',    value: quality.stale_signal_count, warn: quality.stale_signal_count > 0 },
              { label: 'Incomplete Quotes',value: quality.incomplete_quotations, warn: quality.incomplete_quotations > 0 },
            ].map((item) => (
              <div key={item.label} className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className={`text-xl font-semibold mt-0.5 ${
                  item.warn ? 'text-amber-600' : item.ok ? 'text-green-600' : 'text-gray-900'
                }`}>{item.value}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm">
            Connect to Exasol and load data to see quality metrics.
          </p>
        )}
      </div>
    </div>
  )
}
