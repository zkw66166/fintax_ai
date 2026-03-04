import { Clock } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import { useChatHistory } from '../hooks/useDashboardData'
import s from './RecentQueries.module.css'

export default function RecentQueries({ onQueryClick }) {
  const { data, loading, error, refetch } = useChatHistory(5)

  const getRouteBadge = (route) => {
    const badges = {
      financial_data: { label: '财务数据', color: '#3b82f6' },
      tax_incentive: { label: '税收优惠', color: '#10b981' },
      regulation: { label: '法规知识', color: '#f59e0b' }
    }
    return badges[route] || { label: '未知', color: '#6b7280' }
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date

    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    return date.toLocaleDateString('zh-CN')
  }

  const handleQueryClick = (query) => {
    if (onQueryClick) {
      onQueryClick(query)
    }
  }

  const queries = data || []

  return (
    <WidgetCard
      title="最近查询"
      icon={Clock}
      size="large"
      loading={loading}
      error={error}
      onRefresh={refetch}
    >
      {queries.length === 0 ? (
        <div className={s.empty}>暂无查询历史</div>
      ) : (
        <div className={s.list}>
          {queries.map((item, i) => {
            const badge = getRouteBadge(item.route)
            return (
              <div
                key={i}
                className={s.item}
                onClick={() => handleQueryClick(item.query)}
              >
                <div className={s.itemHeader}>
                  <span
                    className={s.badge}
                    style={{ backgroundColor: badge.color }}
                  >
                    {badge.label}
                  </span>
                  <span className={s.time}>{formatTime(item.timestamp)}</span>
                </div>
                <div className={s.query}>{item.query}</div>
              </div>
            )
          })}
        </div>
      )}
    </WidgetCard>
  )
}
