import s from './ProgressBar.module.css'

const COLOR_MAP = {
  blue: '#2563eb',
  green: '#16a34a',
  orange: '#d97706',
  red: '#dc2626',
  purple: '#9333ea',
}

export default function ProgressBar({ label, percent, color = 'blue' }) {
  const pct = Math.min(100, Math.max(0, percent || 0))
  const bg = COLOR_MAP[color] || color
  return (
    <div className={s.wrap}>
      {label && <span className={s.label}>{label}</span>}
      <div className={s.track}>
        <div className={s.fill} style={{ width: `${pct}%`, background: bg }} />
      </div>
      <span className={s.pct}>{pct.toFixed(0)}%</span>
    </div>
  )
}
