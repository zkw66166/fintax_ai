import s from './MetricDisplay.module.css'

export default function MetricDisplay({ label, value, unit = '', trend = null, level = null }) {
  const getLevelColor = (lvl) => {
    if (!lvl) return null
    const map = {
      excellent: 'var(--color-success)',
      good: 'var(--color-success)',
      normal: 'var(--color-warning)',
      warning: 'var(--color-warning)',
      risk: 'var(--color-error)',
      poor: 'var(--color-error)'
    }
    return map[lvl.toLowerCase()] || null
  }

  const levelColor = getLevelColor(level)

  return (
    <div className={s.metric}>
      <div className={s.label}>{label}</div>
      <div className={s.valueRow}>
        <span className={s.value} style={levelColor ? { color: levelColor } : {}}>
          {value}
        </span>
        {unit && <span className={s.unit}>{unit}</span>}
        {trend !== null && <TrendIndicator value={trend} />}
      </div>
      {level && (
        <span className={s.level} style={{ color: levelColor }}>
          {level}
        </span>
      )}
    </div>
  )
}

function TrendIndicator({ value }) {
  if (value === 0) return null

  const isPositive = value > 0
  const color = isPositive ? 'var(--color-success)' : 'var(--color-error)'
  const arrow = isPositive ? '↑' : '↓'

  return (
    <span className={s.trend} style={{ color }}>
      {arrow} {Math.abs(value).toFixed(1)}%
    </span>
  )
}
