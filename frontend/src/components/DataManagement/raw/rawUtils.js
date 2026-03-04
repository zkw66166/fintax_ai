/**
 * Shared utilities for raw format financial statement rendering.
 */

/** Format a numeric value with thousands separator and 2 decimal places. */
export function formatAmount(val) {
  if (val == null || val === '') return ''
  const num = Number(val)
  if (isNaN(num)) return val
  if (num === 0) return '0.00'
  const fixed = Math.abs(num).toFixed(2)
  const parts = fixed.split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return (num < 0 ? '-' : '') + parts.join('.')
}

/** Format a rate value as percentage (e.g. 0.25 -> "25%"). */
export function formatRate(val) {
  if (val == null || val === '') return ''
  const num = Number(val)
  if (isNaN(num)) return val
  return (num * 100).toFixed(0) + '%'
}
