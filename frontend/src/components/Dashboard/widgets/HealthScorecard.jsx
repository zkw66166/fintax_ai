import { Activity } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import MetricDisplay from '../shared/MetricDisplay'
import { useProfileData } from '../hooks/useDashboardData'
import s from './HealthScorecard.module.css'

export default function HealthScorecard({ companyId, onNavigate }) {
  const { data, loading, error, refetch } = useProfileData(companyId)

  if (!companyId) {
    return (
      <WidgetCard title="公司健康度" icon={Activity} size="large">
        <div className={s.empty}>请选择公司</div>
      </WidgetCard>
    )
  }

  // Helper function to flatten grouped metrics into a map
  const flattenMetrics = (groupedMetrics) => {
    const flat = {}
    if (!groupedMetrics) return flat

    // groupedMetrics is like: { "偿债能力": [{code: "debt_ratio", ...}], ... }
    for (const category of Object.values(groupedMetrics)) {
      if (Array.isArray(category)) {
        for (const metric of category) {
          if (metric.code) {
            flat[metric.code] = {
              value: metric.value,
              evaluation_level: metric.eval_level,
              unit: metric.unit,
              name: metric.name
            }
          }
        }
      }
    }
    return flat
  }

  const calculateHealthScore = (profile) => {
    if (!profile?.financial_metrics) return 0

    const metrics = flattenMetrics(profile.financial_metrics)
    const weights = {
      debt_ratio: 0.2,
      current_ratio: 0.15,
      roe: 0.25,
      gross_margin: 0.2,
      revenue_growth: 0.2
    }

    const scores = {
      debt_ratio: getMetricScore(metrics.debt_ratio, 'debt_ratio'),
      current_ratio: getMetricScore(metrics.current_ratio, 'current_ratio'),
      roe: getMetricScore(metrics.roe, 'roe'),
      gross_margin: getMetricScore(metrics.gross_margin, 'gross_margin'),
      revenue_growth: getMetricScore(metrics.revenue_growth, 'revenue_growth')
    }

    let totalScore = 0
    for (const [key, weight] of Object.entries(weights)) {
      totalScore += (scores[key] || 0) * weight
    }

    return Math.round(totalScore)
  }

  const getMetricScore = (metric, type) => {
    if (!metric?.value && metric?.value !== 0) return 50

    const value = parseFloat(metric.value)
    const level = metric.evaluation_level?.toLowerCase() || metric.eval_level?.toLowerCase()

    const levelScores = {
      excellent: 100,
      优: 100,
      good: 80,
      良: 80,
      normal: 60,
      中: 60,
      warning: 40,
      差: 40,
      risk: 20,
      poor: 20
    }

    return levelScores[level] || 50
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--color-success)'
    if (score >= 60) return 'var(--color-warning)'
    return 'var(--color-error)'
  }

  const getScoreLevel = (score) => {
    if (score >= 80) return '优秀'
    if (score >= 60) return '良好'
    return '需改进'
  }

  const healthScore = data ? calculateHealthScore(data) : 0
  const scoreColor = getScoreColor(healthScore)
  const scoreLevel = getScoreLevel(healthScore)

  const flatMetrics = data?.financial_metrics ? flattenMetrics(data.financial_metrics) : {}

  const keyMetrics = [
    {
      label: '资产负债率',
      value: flatMetrics.debt_ratio?.value ?? '-',
      unit: '%',
      level: flatMetrics.debt_ratio?.evaluation_level || flatMetrics.debt_ratio?.eval_level
    },
    {
      label: '净资产收益率',
      value: flatMetrics.roe?.value ?? '-',
      unit: '%',
      level: flatMetrics.roe?.evaluation_level || flatMetrics.roe?.eval_level
    },
    {
      label: '毛利率',
      value: flatMetrics.gross_margin?.value ?? '-',
      unit: '%',
      level: flatMetrics.gross_margin?.evaluation_level || flatMetrics.gross_margin?.eval_level
    },
    {
      label: '营收增长率',
      value: flatMetrics.revenue_growth?.value ?? '-',
      unit: '%',
      level: flatMetrics.revenue_growth?.evaluation_level || flatMetrics.revenue_growth?.eval_level
    }
  ]

  return (
    <WidgetCard
      title="公司健康度"
      icon={Activity}
      size="large"
      loading={loading}
      error={error}
      onRefresh={refetch}
      actions={[
        { label: '查看详情', onClick: () => onNavigate && onNavigate('profile') }
      ]}
    >
      <div className={s.container}>
        <div className={s.scoreSection}>
          <div className={s.scoreCircle} style={{ borderColor: scoreColor }}>
            <div className={s.scoreValue} style={{ color: scoreColor }}>
              {healthScore}
            </div>
            <div className={s.scoreLabel}>综合评分</div>
          </div>
          <div className={s.scoreLevel} style={{ color: scoreColor }}>
            {scoreLevel}
          </div>
        </div>

        <div className={s.metricsGrid}>
          {keyMetrics.map((metric, i) => (
            <MetricDisplay
              key={i}
              label={metric.label}
              value={metric.value}
              unit={metric.unit}
              level={metric.level}
            />
          ))}
        </div>
      </div>
    </WidgetCard>
  )
}
