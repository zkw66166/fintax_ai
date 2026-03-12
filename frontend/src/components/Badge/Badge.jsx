import s from './Badge.module.css'

export default function Badge({ label, color, size = 'small', className = '' }) {
  return (
    <span
      className={`${s.badge} ${s[size]} ${className}`}
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  )
}
