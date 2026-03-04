import s from './ProgressBar.module.css'

const COLOR_MAP = {
  blue: '#93c5fd',
  green: '#86efac',
  orange: '#fcd34d',
  red: '#fca5a5',
  purple: '#c4b5fd',
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
