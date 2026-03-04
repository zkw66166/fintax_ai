import { useState, useEffect } from 'react'
import { Briefcase, ArrowRight } from 'lucide-react'
import WidgetCard from '../shared/WidgetCard'
import { useCompaniesOverview } from '../hooks/useDashboardData'
import s from './ClientPortfolio.module.css'

export default function ClientPortfolio({ onCompanySelect, onPageChange }) {
  const { data, loading, error, refetch } = useCompaniesOverview()
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(5)
  const [jumpPage, setJumpPage] = useState('')
  const [qualityData, setQualityData] = useState({})
  const [healthScores, setHealthScores] = useState({})

  const companies = data?.companies || []

  // Fetch quality check data for all companies
  useEffect(() => {
    if (!companies.length) return

    const fetchQualityChecks = async () => {
      const token = localStorage.getItem('access_token')
      const results = {}

      await Promise.all(
        companies.map(async (company) => {
          try {
            const response = await fetch(
              `/api/data-management/quality-check?company_id=${company.taxpayer_id}`,
              {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                }
              }
            )
            if (response.ok) {
              const data = await response.json()
              results[company.taxpayer_id] = data.summary?.pass_rate || 0
            }
          } catch (err) {
            console.error(`Quality check failed for ${company.taxpayer_id}:`, err)
          }
        })
      )

      setQualityData(results)
    }

    fetchQualityChecks()
  }, [companies])

  // Fetch health scores for all companies
  useEffect(() => {
    if (!companies.length) return

    const fetchHealthScores = async () => {
      const token = localStorage.getItem('access_token')
      const scores = {}

      await Promise.all(
        companies.map(async (company) => {
          try {
            const response = await fetch(
              `/api/profile/${company.taxpayer_id}?year=2025`,
              {
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                }
              }
            )
            if (response.ok) {
              const profile = await response.json()
              scores[company.taxpayer_id] = calculateHealthScore(profile)
            }
          } catch (err) {
            console.error(`Profile fetch failed for ${company.taxpayer_id}:`, err)
          }
        })
      )

      setHealthScores(scores)
    }

    fetchHealthScores()
  }, [companies])

  const flattenMetrics = (groupedMetrics) => {
    const flat = {}
    if (!groupedMetrics) return flat

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

    const getMetricScore = (metric) => {
      if (!metric?.value && metric?.value !== 0) return 50
      const level = metric.evaluation_level?.toLowerCase() || metric.eval_level?.toLowerCase()
      const levelScores = {
        excellent: 100, 优: 100,
        good: 80, 良: 80,
        normal: 60, 中: 60,
        warning: 40, 差: 40,
        risk: 20, poor: 20
      }
      return levelScores[level] || 50
    }

    const scores = {
      debt_ratio: getMetricScore(metrics.debt_ratio),
      current_ratio: getMetricScore(metrics.current_ratio),
      roe: getMetricScore(metrics.roe),
      gross_margin: getMetricScore(metrics.gross_margin),
      revenue_growth: getMetricScore(metrics.revenue_growth)
    }

    let totalScore = 0
    for (const [key, weight] of Object.entries(weights)) {
      totalScore += (scores[key] || 0) * weight
    }

    return Math.round(totalScore)
  }

  const getPassRateClass = (rate) => {
    if (rate >= 90) return s.statusComplete
    if (rate >= 70) return s.statusPartial
    return s.statusMissing
  }

  const getScoreClass = (score) => {
    if (score >= 80) return s.scoreExcellent
    if (score >= 60) return s.scoreGood
    return s.scorePoor
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN')
  }

  const handleRowClick = (company) => {
    if (onCompanySelect) {
      onCompanySelect(company.taxpayer_id)
    }
  }

  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value))
    setCurrentPage(1)
  }

  const handleJumpToPage = () => {
    const page = Number(jumpPage)
    const totalPages = Math.ceil(companies.length / pageSize)
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
      setJumpPage('')
    }
  }

  const totalPages = Math.ceil(companies.length / pageSize)
  const startIdx = (currentPage - 1) * pageSize
  const endIdx = startIdx + pageSize
  const paginatedCompanies = companies.slice(startIdx, endIdx)

  return (
    <WidgetCard
      title="客户组合总览"
      icon={Briefcase}
      size="full"
      loading={loading}
      error={error}
      onRefresh={refetch}
    >
      {companies.length === 0 ? (
        <div className={s.empty}>暂无客户数据</div>
      ) : (
        <>
          <table className={s.table}>
            <thead>
              <tr>
                <th>公司名称</th>
                <th>纳税人类型</th>
                <th>数据状态</th>
                <th>最后更新</th>
                <th>健康评分</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {paginatedCompanies.map((company) => {
                const scoreClass = getScoreClass(healthScores[company.taxpayer_id] || 0)

                return (
                  <tr key={company.taxpayer_id} onClick={() => handleRowClick(company)}>
                    <td className={s.companyName}>{company.taxpayer_name || company.company_name}</td>
                    <td>{company.taxpayer_type}</td>
                    <td>
                      {qualityData[company.taxpayer_id] !== undefined ? (
                        <span className={`${s.status} ${getPassRateClass(qualityData[company.taxpayer_id])}`}>
                          {qualityData[company.taxpayer_id].toFixed(1)}%
                        </span>
                      ) : (
                        <span className={s.statusLoading}>检查中...</span>
                      )}
                    </td>
                    <td>{formatDate(company.last_update)}</td>
                    <td className={`${s.score} ${scoreClass}`}>
                      {healthScores[company.taxpayer_id] !== undefined
                        ? healthScores[company.taxpayer_id]
                        : '-'}
                    </td>
                    <td>
                      <div className={s.actions}>
                        <button
                          className={s.actionBtn}
                          onClick={(e) => {
                            e.stopPropagation()
                            if (onCompanySelect) {
                              onCompanySelect(company.taxpayer_id)
                            }
                            if (onPageChange) {
                              onPageChange('profile')
                            }
                          }}
                        >
                          画像
                        </button>
                        <button
                          className={s.actionBtn}
                          onClick={(e) => {
                            e.stopPropagation()
                            if (onCompanySelect) {
                              onCompanySelect(company.taxpayer_id)
                            }
                            if (onPageChange) {
                              onPageChange('data-management')
                            }
                          }}
                        >
                          数据
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {companies.length > pageSize && (
            <div className={s.pagination}>
              <div className={s.paginationLeft}>
                <button
                  className={s.pageButton}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  上一页
                </button>
                <span className={s.pageInfo}>
                  第 {currentPage} 页 / 共 {totalPages} 页
                </span>
                <button
                  className={s.pageButton}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  下一页
                </button>
              </div>

              <div className={s.paginationRight}>
                <span>每页显示</span>
                <select
                  className={s.pageSizeSelect}
                  value={pageSize}
                  onChange={handlePageSizeChange}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                </select>
                <span>条</span>

                <span>跳转到</span>
                <input
                  type="number"
                  className={s.jumpInput}
                  value={jumpPage}
                  onChange={(e) => setJumpPage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleJumpToPage()}
                  min={1}
                  max={totalPages}
                  placeholder="页码"
                />
                <button className={s.jumpButton} onClick={handleJumpToPage} title="跳转到指定页">
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </WidgetCard>
  )
}
