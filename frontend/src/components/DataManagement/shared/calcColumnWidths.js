/**
 * Column width calculation utility for MonoTable.
 * Uses canvas measureText for accurate text width estimation.
 */

export const TYPE_WIDTHS = {
  amount: { min: 120, max: 260 },
  enum:   { min: 90,  max: 140 },
  name:   { min: 160, max: 320 },
  id:     { min: 200, max: 360 },
  text:   { min: 120, max: 260 },
}

export const CELL_PADDING = 24
export const HEADER_FONT = '700 13px system-ui, "PingFang SC", "Microsoft YaHei", sans-serif'
export const CELL_FONT = '400 13px system-ui, "PingFang SC", "Microsoft YaHei", sans-serif'
export const MAX_SAMPLE_ROWS = 100

let _ctx = null

export function getCanvasContext() {
  if (!_ctx) {
    const canvas = document.createElement('canvas')
    _ctx = canvas.getContext('2d')
  }
  return _ctx
}

function measureText(ctx, text, font) {
  ctx.font = font
  return ctx.measureText(text).width
}

/**
 * Split a Chinese header label into at most 2 lines for width estimation.
 * Tries natural break points (parenthesis, slash, dash) before midpoint.
 */
function splitHeader(label) {
  if (!label || label.length <= 4) return [label || '']
  const breaks = ['（', '(', '/', '—', '-', '·']
  for (const ch of breaks) {
    const idx = label.indexOf(ch)
    if (idx > 0 && idx < label.length - 1) {
      return [label.slice(0, idx), label.slice(idx)]
    }
  }
  const mid = Math.ceil(label.length / 2)
  return [label.slice(0, mid), label.slice(mid)]
}

function isAllZero(values) {
  const nonEmpty = values.filter(v => v !== null && v !== undefined && v !== '')
  if (nonEmpty.length === 0) return true
  return nonEmpty.every(v => {
    const n = Number(v)
    return !isNaN(n) && n === 0
  })
}

function percentile(arr, p) {
  if (arr.length === 0) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const idx = Math.min(Math.floor(sorted.length * p), sorted.length - 1)
  return sorted[idx]
}

/**
 * Calculate optimal column widths based on header text and data content.
 * @param {Array<{key, label, col_type?, align?}>} columns
 * @param {Array<Object>} rows
 * @returns {number[]} pixel widths, same order as columns
 */
export default function calcColumnWidths(columns, rows) {
  const ctx = getCanvasContext()
  if (!ctx) return columns.map(col => (TYPE_WIDTHS[col.col_type] || TYPE_WIDTHS.text).min)

  const sampleRows = rows.slice(0, MAX_SAMPLE_ROWS)

  return columns.map(col => {
    const bounds = TYPE_WIDTHS[col.col_type] || TYPE_WIDTHS.text

    // Header width estimate
    const lines = splitHeader(col.label)
    let headerEst = 0
    for (const line of lines) {
      const w = measureText(ctx, line, HEADER_FONT)
      if (w > headerEst) headerEst = w
    }

    // Data width estimate (P95)
    const values = sampleRows.map(r => r[col.key])
    let dataEst = 0

    if (isAllZero(values)) {
      // All-zero column: don't shrink, use minWidth as floor
      dataEst = 0
    } else {
      const widths = values
        .map(v => measureText(ctx, String(v ?? ''), CELL_FONT))
        .filter(w => w > 0)
      dataEst = percentile(widths, 0.95)
    }

    const raw = Math.max(bounds.min, headerEst, dataEst) + CELL_PADDING
    return Math.max(bounds.min, Math.min(bounds.max, raw))
  })
}
