import { useState, useEffect, useRef } from 'react'
import s from './MonoTable.module.css'
import calcColumnWidths, {
  TYPE_WIDTHS, CELL_PADDING, getCanvasContext, HEADER_FONT, CELL_FONT, MAX_SAMPLE_ROWS,
} from './calcColumnWidths'

export default function MonoTable({ columns, rows, borderless = false, className = '' }) {
  const [colWidths, setColWidths] = useState([])
  const [resizing, setResizing] = useState(null)
  const [tooltip, setTooltip] = useState(null)
  const containerRef = useRef(null)

  // Recalculate widths when data changes
  useEffect(() => {
    if (columns.length > 0) {
      setColWidths(calcColumnWidths(columns, rows))
    }
  }, [columns, rows])

  // Resize drag listeners
  useEffect(() => {
    if (!resizing) return
    const { colIndex, startX, startWidth } = resizing
    const bounds = TYPE_WIDTHS[columns[colIndex]?.col_type] || TYPE_WIDTHS.text

    function onMove(e) {
      const delta = e.clientX - startX
      const newWidth = Math.max(bounds.min, Math.min(bounds.max, startWidth + delta))
      setColWidths(prev => {
        const next = [...prev]
        next[colIndex] = newWidth
        return next
      })
    }
    function onUp() { setResizing(null) }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [resizing, columns])

  // No frozen columns
  const frozenCount = 0

  const totalWidth = colWidths.reduce((a, b) => a + b, 0)

  function formatCell(col, value) {
    if (value === null || value === undefined || value === '') return ''
    if (col.col_type === 'enum') return value
    if (col.col_type === 'amount' || col.align === 'right') {
      const n = Number(value)
      if (!isNaN(n) && isFinite(n)) return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    }
    return value
  }

  function handleResizeStart(e, colIndex) {
    e.preventDefault()
    e.stopPropagation()
    setResizing({ colIndex, startX: e.clientX, startWidth: colWidths[colIndex] || 120 })
  }

  function handleAutoFit(colIndex) {
    const col = columns[colIndex]
    const ctx = getCanvasContext()
    if (!ctx) return
    const bounds = TYPE_WIDTHS[col.col_type] || TYPE_WIDTHS.text
    ctx.font = CELL_FONT
    let maxW = 0
    for (const row of rows.slice(0, MAX_SAMPLE_ROWS)) {
      const w = ctx.measureText(String(row[col.key] ?? '')).width
      if (w > maxW) maxW = w
    }
    ctx.font = HEADER_FONT
    const headerW = ctx.measureText(col.label || '').width
    const fitted = Math.max(bounds.min, Math.min(bounds.max, Math.max(maxW, headerW) + CELL_PADDING))
    setColWidths(prev => {
      const next = [...prev]
      next[colIndex] = fitted
      return next
    })
  }

  function handleHeaderHover(e, label) {
    if (!label || label.length <= 4) return
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    setTooltip({
      text: label,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top + 24,
    })
  }

  function thClass(i) {
    const parts = [s.th]
    if (columns[i]?.align === 'right') parts.push(s.alignRight)
    if (i < frozenCount) {
      parts.push(s.frozen)
      if (i === frozenCount - 1) parts.push(s.frozenShadow)
    }
    return parts.join(' ')
  }

  function tdClass(j) {
    const parts = [s.td]
    if (columns[j]?.align === 'right') parts.push(s.alignRight)
    if (j < frozenCount) {
      parts.push(s.frozen)
      if (j === frozenCount - 1) parts.push(s.frozenShadow)
    }
    return parts.join(' ')
  }

  return (
    <div
      className={`${s.tableContainer} ${resizing ? s.resizing : ''}`}
      ref={containerRef}
    >
      <table
        className={`${s.table} ${borderless ? s.borderless : ''} ${className}`}
        style={{
          width: totalWidth > 0 ? totalWidth : undefined,
          tableLayout: colWidths.length > 0 ? 'fixed' : 'auto',
        }}
      >
        {colWidths.length > 0 && (
          <colgroup>
            {colWidths.map((w, i) => (
              <col key={i} style={{ width: w }} />
            ))}
          </colgroup>
        )}
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th
                key={col.key}
                className={thClass(i)}
                style={i < frozenCount ? { left: frozenLeftOffsets[i], position: 'sticky' } : undefined}
                onMouseEnter={(e) => handleHeaderHover(e, col.label)}
                onMouseLeave={() => setTooltip(null)}
              >
                <span className={s.headerText}>{col.label}</span>
                <div
                  className={s.resizeHandle}
                  onMouseDown={(e) => handleResizeStart(e, i)}
                  onDoubleClick={() => handleAutoFit(i)}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col, j) => (
                <td
                  key={col.key}
                  className={tdClass(j)}
                  style={j < frozenCount ? { left: frozenLeftOffsets[j], position: 'sticky' } : undefined}
                >
                  {formatCell(col, row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {tooltip && (
        <div
          className={s.tooltip}
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  )
}
