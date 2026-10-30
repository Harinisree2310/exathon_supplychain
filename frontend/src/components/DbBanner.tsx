import React from 'react'
import axios from 'axios'
import { AlertTriangle } from 'lucide-react'

interface DbBannerProps {
  error: unknown
}

export default function DbBanner({ error }: DbBannerProps) {
  const is503 = axios.isAxiosError(error) && error.response?.status === 503
  if (!is503) return null

  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
      <div>
        <p className="font-medium text-amber-800">Exasol not connected</p>
        <p className="text-sm text-amber-700 mt-1">
          Start Exasol Personal with the one-line installer, then reload this page.
        </p>
        <pre className="mt-2 overflow-x-auto rounded-lg bg-amber-100 p-2 text-xs text-amber-900">
          irm https://www.exasol.com/install/starter-kit.ps1 | iex
        </pre>
      </div>
    </div>
  )
}
