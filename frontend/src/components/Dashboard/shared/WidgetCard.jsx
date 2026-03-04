import { RefreshCw } from 'lucide-react'
import s from './WidgetCard.module.css'

export default function WidgetCard({
  title,
  icon: Icon,
  size = 'medium',
  loading = false,
  error = null,
  onRefresh,
  actions = [],
  children
}) {
  return (
    <div className={`${s.card} ${s[size]}`}>
      <div className={s.header}>
        <div className={s.titleRow}>
          {Icon && <Icon size={18} className={s.icon} />}
          <h3 className={s.title}>{title}</h3>
        </div>
        <div className={s.actions}>
          {actions.map((action, i) => (
            <button
              key={i}
              className={s.actionBtn}
              onClick={action.onClick}
              title={action.label}
            >
              {action.label}
            </button>
          ))}
          {onRefresh && (
            <button
              className={s.refreshBtn}
              onClick={onRefresh}
              disabled={loading}
              title="刷新"
            >
              <RefreshCw size={16} className={loading ? s.spinning : ''} />
            </button>
          )}
        </div>
      </div>
      <div className={s.content}>
        {loading && <div className={s.loading}>加载中...</div>}
        {error && <div className={s.error}>{error}</div>}
        {!loading && !error && children}
      </div>
    </div>
  )
}
