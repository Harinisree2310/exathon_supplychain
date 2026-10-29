import React from 'react'
import { AlertTriangle } from 'lucide-react'

interface DbBannerProps {
  error: unknown
}

export default function DbBanner({ error }: DbBannerProps) {
  const is503 = (error as any)?.response?.status === 503
  if (!is503) return null

  return (
    <div className="m-6 p-4 bg-amber-50 border border-amber-300 rounded-lg flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
      <div>
        <p className="font-medium text-amber-800">Exasol not connected</p>
        <p className="text-sm text-amber-700 mt-1">
          Start Exasol Personal with the one-line installer, then reload this page.
        </p>
        <pre className="mt-2 text-xs bg-amber-100 rounded p-2 text-amber-900">
          irm https://www.exasol.com/install/starter-kit.ps1 | iex
        </pre>
      </div>
    </div>
  )
}
