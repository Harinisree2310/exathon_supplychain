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
    warning: 'border-amber-300 bg-amber-50',
    danger:  'border-red-300 bg-red-50',
    success: 'border-green-300 bg-green-50',
  }[variant]

  return (
    <div className={clsx('card', variantClass)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
          {loading ? (
            <div className="mt-2 h-8 w-24 bg-gray-200 rounded animate-pulse" />
          ) : (
            <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
          )}
          {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
        </div>
        {icon && (
          <div className="ml-4 text-gray-400">{icon}</div>
        )}
      </div>
    </div>
  )
}
