import s from './EvalLabel.module.css'

const TYPE_CLASS = {
  positive: s.positive,
  growth: s.growth,
  neutral: s.neutral,
  warning: s.warning,
  negative: s.negative,
  purple: s.purple,
  orange: s.orange,
}

export default function EvalLabel({ level, type }) {
  if (!level) return null
  return (
    <span className={`${s.label} ${TYPE_CLASS[type] || s.neutral}`}>
      {level}
    </span>
  )
}
