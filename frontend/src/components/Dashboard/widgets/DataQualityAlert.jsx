import { AlertTriangle } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import { useQualityCheck } from '../hooks/useDashboardData'
import s from './DataQualityAlert.module.css'

export default function DataQualityAlert({ companyId }) {
  const { data, loading, error, runCheck } = useQualityCheck(companyId)

  if (!companyId) {
    return (
      <WidgetCard title="数据质量告警" icon={AlertTriangle} size="medium">
        <div className={s.empty}>请选择公司</div>
      </WidgetCard>
    )
  }

  const calculatePassRate = (result) => {
    if (!result?.summary) return 0
    return result.summary.pass_rate || 0
  }

  const getCategoryStats = (result) => {
    if (!result?.summary?.by_category) return {}

    const byCategory = result.summary.by_category
    const stats = {
      internal_consistency: byCategory.internal_consistency || { passed: 0, total: 0 },
      reasonableness: byCategory.reasonableness || { passed: 0, total: 0 },
      cross_table: byCategory.cross_table || { passed: 0, total: 0 },
      period_continuity: byCategory.period_continuity || { passed: 0, total: 0 },
      completeness: byCategory.completeness || { passed: 0, total: 0 }
    }

    return stats
  }

  const getTopIssues = (result) => {
    if (!result?.domains) return []

    const issues = []

    for (const domain of result.domains) {
      for (const detail of domain.details || []) {
        if (detail.severity === 'error' && detail.status === 'fail') {
          issues.push({
            domain: domain.domain_name_cn,
            message: detail.message || detail.rule_name_cn,
            rule: detail.rule_id
          })
        }
      }
    }

    return issues.slice(0, 3)
  }

  const passRate = data ? calculatePassRate(data) : 0
  const categoryStats = data ? getCategoryStats(data) : {}
  const topIssues = data ? getTopIssues(data) : []

  const getScoreColor = (rate) => {
    if (rate >= 90) return 'var(--color-success)'
    if (rate >= 70) return 'var(--color-warning)'
    return 'var(--color-error)'
  }

  const categoryLabels = {
    internal_consistency: '内部一致性',
    reasonableness: '合理性',
    cross_table: '跨表一致性',
    period_continuity: '期间连续性',
    completeness: '完整性'
  }

  return (
    <WidgetCard
      title="数据质量告警"
      icon={AlertTriangle}
      size="medium"
      loading={loading}
      error={error}
    >
      <div className={s.container}>
        {data ? (
          <>
            <div className={s.overallScore}>
              <div className={s.scoreValue} style={{ color: getScoreColor(passRate) }}>
                {passRate}%
              </div>
              <div className={s.scoreLabel}>总体通过率</div>
            </div>

            <div className={s.categories}>
              {Object.entries(categoryStats).map(([key, stats]) => (
                <div key={key} className={s.category}>
                  <span className={s.categoryName}>{categoryLabels[key]}</span>
                  <span className={s.categoryStats}>
                    <span className={s.pass}>{stats.passed}</span>
                    {' / '}
                    <span>{stats.total}</span>
                  </span>
                </div>
              ))}
            </div>

            {topIssues.length > 0 && (
              <div className={s.issues}>
                <div className={s.issuesTitle}>关键问题 (Top 3)</div>
                <div className={s.issuesList}>
                  {topIssues.map((issue, i) => (
                    <div key={i} className={s.issue}>
                      [{issue.domain}] {issue.message}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button className={s.runButton} onClick={runCheck} disabled={loading}>
              重新检查
            </button>
          </>
        ) : (
          <button className={s.runButton} onClick={runCheck} disabled={loading}>
            运行完整检查
          </button>
        )}
      </div>
    </WidgetCard>
  )
}
