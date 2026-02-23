import EvalLabel from './EvalLabel'
import s from './CompactMetric.module.css'

export default function CompactMetric({ label, value, unit, evalData, suffix }) {
  return (
    <div className={s.row}>
      <span className={s.label}>{label}</span>
      <span className={s.value}>{value ?? '—'}</span>
      {unit && <span className={s.unit}>{unit}</span>}
      {suffix && <span className={s.suffix}>{suffix}</span>}
      {evalData && <EvalLabel level={evalData.level} type={evalData.type} />}
    </div>
  )
}
