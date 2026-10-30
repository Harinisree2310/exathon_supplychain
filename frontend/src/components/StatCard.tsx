import React from 'react'
import clsx from 'clsx'

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon?: React.ReactNode
  variant?: 'default' | 'warning' | 'danger' | 'success'
  loading?: boolean
}

export default function StatCard({ label, value, sub, icon, variant = 'default', loading }: StatCardProps) {
  const variantClass = {
    default: 'border-gray-200',
    warning: 'border-amber-200 bg-amber-50/50',
    danger:  'border-red-200 bg-red-50/50',
    success: 'border-emerald-200 bg-emerald-50/50',
  }[variant]

  return (
    <div className={clsx('card stat-card', variantClass)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-gray-500">{label}</p>
          {loading ? (
            <div className="mt-3 h-8 w-24 rounded-md bg-gray-200 animate-pulse" />
          ) : (
            <p className="mt-2 text-[26px] font-semibold leading-none tracking-tight text-gray-900">{value}</p>
          )}
          {sub && <p className="mt-2 text-xs text-gray-500">{sub}</p>}
        </div>
        {icon && (
          <div className="stat-icon ml-3">{icon}</div>
        )}
      </div>
    </div>
  )
}
