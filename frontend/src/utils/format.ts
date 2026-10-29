/** Format a number as Indian Rupees. */
export function formatINR(value: number | null | undefined, compact = false): string {
  if (value == null) return '—'
  if (compact) {
    if (value >= 1_00_00_000) return `₹${(value / 1_00_00_000).toFixed(2)} Cr`
    if (value >= 1_00_000)   return `₹${(value / 1_00_000).toFixed(2)} L`
    if (value >= 1_000)      return `₹${(value / 1_000).toFixed(1)} K`
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)
}

/** Format a percentage. */
export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value == null) return '—'
  return `${value.toFixed(digits)}%`
}

/** Concentration badge colour class. */
export function concentrationClass(level: string): string {
  if (level === 'HIGH')   return 'badge-high'
  if (level === 'MEDIUM') return 'badge-medium'
  return 'badge-low'
}

/** Action code → human-readable label. */
export function actionLabel(code: string): string {
  const map: Record<string, string> = {
    SWITCH_SUPPLIER: 'Switch Supplier',
    SPLIT_ORDERS:    'Split Orders',
    VERIFY_FIRST:    'Verify First',
    ACCEPT_COST:     'Accept Cost',
    NO_ACTION:       'No Action',
  }
  return map[code] ?? code
}

/** Action code → Tailwind colour class. */
export function actionClass(code: string): string {
  const map: Record<string, string> = {
    SWITCH_SUPPLIER: 'text-green-700 bg-green-100',
    SPLIT_ORDERS:    'text-blue-700 bg-blue-100',
    VERIFY_FIRST:    'text-amber-700 bg-amber-100',
    ACCEPT_COST:     'text-gray-700 bg-gray-100',
    NO_ACTION:       'text-gray-500 bg-gray-50',
  }
  return map[code] ?? 'text-gray-700 bg-gray-100'
}
