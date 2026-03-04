import { useState, useEffect } from 'react'
import s from './MultiCompanyData.module.css'
import {
  fetchCompaniesOverview,
  recalculateMetricsAll,
  reloadReferenceData,
  batchQualityCheck,
  clearCache,
  reloadConfig
} from '../../services/dataManagementApi'
import useAuth from '../../hooks/useAuth'
import { Users, Search, Filter, Download, Building2, Calendar, RefreshCw } from 'lucide-react'

export default function MultiCompanyData() {
  const { isAdmin } = useAuth()
  const { user } = useAuth()
  const isSys = user?.role === 'sys'
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState({
    metrics: false,
    reference: false,
    quality: false,
    cache: false,
    config: false
  })
  const [updateResult, setUpdateResult] = useState(null)

  useEffect(() => {
    fetchCompaniesOverview()
      .then(setData)
      .catch(() => { })
      .finally(() => setLoading(false))
  }, [])

  const handleRecalculateMetrics = async () => {
    if (!confirm('确认重新计算所有企业的财务指标？\n\n此操作将覆盖现有指标数据，耗时约15-30秒。')) {
      return
    }

    setUpdating(prev => ({ ...prev, metrics: true }))
    setUpdateResult(null)

    try {
      const result = await recalculateMetricsAll('both')
      setUpdateResult({
        success: result.success,
        message: result.message,
        details: result.details ? {
          '企业数': `${result.details.total_companies} 家`,
          'v1指标': `${result.details.v1_total_count} 条`,
          'v2指标': `${result.details.v2_total_count} 条`,
          '耗时': `${(result.details.duration_ms / 1000).toFixed(2)} 秒`
        } : null
      })

      // 3秒后自动刷新企业列表
      setTimeout(() => {
        fetchCompaniesOverview().then(setData).catch(() => {})
        setUpdateResult(null)
      }, 3000)
    } catch (error) {
      setUpdateResult({
        success: false,
        message: error.message || '财务指标重算失败'
      })
    } finally {
      setUpdating(prev => ({ ...prev, metrics: false }))
    }
  }

  const handleReloadReferenceData = async () => {
    if (!confirm('确认重新加载参考数据？\n\n此操作将重载同义词表、科目字典、指标定义等配置数据。')) {
      return
    }

    setUpdating(prev => ({ ...prev, reference: true }))
    setUpdateResult(null)

    try {
      const result = await reloadReferenceData()
      setUpdateResult({
        success: result.success,
        message: result.message,
        details: result.affected_tables ? {
          '影响表数': result.affected_tables.length,
          '耗时': `${result.duration_seconds?.toFixed(2)} 秒`
        } : null
      })

      setTimeout(() => setUpdateResult(null), 3000)
    } catch (error) {
      setUpdateResult({
        success: false,
        message: error.message || '参考数据重载失败'
      })
    } finally {
      setUpdating(prev => ({ ...prev, reference: false }))
    }
  }

  const handleBatchQualityCheck = async () => {
    if (!confirm('确认批量检查所有企业的数据质量？\n\n此操作将检查数据一致性、合理性、完整性等，耗时约5-10秒。')) {
      return
    }

    setUpdating(prev => ({ ...prev, quality: true }))
    setUpdateResult(null)

    try {
      const result = await batchQualityCheck('all')
      setUpdateResult({
        success: result.success,
        message: `检查完成：共 ${result.total_taxpayers} 家企业`,
        details: result.summary ? {
          '总问题数': result.summary.total_issues,
          '严重问题': result.summary.critical_issues,
          '警告问题': result.summary.warning_issues,
          '耗时': `${result.duration_seconds?.toFixed(2)} 秒`
        } : null
      })

      setTimeout(() => setUpdateResult(null), 5000)
    } catch (error) {
      setUpdateResult({
        success: false,
        message: error.message || '批量质量检查失败'
      })
    } finally {
      setUpdating(prev => ({ ...prev, quality: false }))
    }
  }

  const handleClearCache = async () => {
    if (!confirm('确认清空内存缓存？\n\n此操作将清空所有查询缓存，后续查询将重新执行SQL和LLM调用。')) {
      return
    }

    setUpdating(prev => ({ ...prev, cache: true }))
    setUpdateResult(null)

    try {
      const result = await clearCache('all')
      setUpdateResult({
        success: result.success,
        message: result.message,
        details: result.cleared_entries ? {
          '意图缓存': result.cleared_entries.intent || 0,
          'SQL缓存': result.cleared_entries.sql || 0,
          '结果缓存': result.cleared_entries.result || 0,
          '跨域缓存': result.cleared_entries.cross_domain || 0,
          '总计': result.cleared_entries.total || 0
        } : null
      })

      setTimeout(() => setUpdateResult(null), 3000)
    } catch (error) {
      setUpdateResult({
        success: false,
        message: error.message || '缓存清理失败'
      })
    } finally {
      setUpdating(prev => ({ ...prev, cache: false }))
    }
  }

  const handleReloadConfig = async () => {
    if (!confirm('确认重新加载意图路由配置？\n\n此操作将重新读取 tax_query_config.json 文件，无需重启应用。')) {
      return
    }

    setUpdating(prev => ({ ...prev, config: true }))
    setUpdateResult(null)

    try {
      const result = await reloadConfig()
      setUpdateResult({
        success: result.success,
        message: result.message,
        details: {
          '配置版本': result.config_version,
          '加载时间': result.loaded_at
        }
      })

      setTimeout(() => setUpdateResult(null), 3000)
    } catch (error) {
      setUpdateResult({
        success: false,
        message: error.message || '配置重载失败'
      })
    } finally {
      setUpdating(prev => ({ ...prev, config: false }))
    }
  }

  if (loading) return <div className={s.loadingArea}><div className={s.spinner}></div>加载中...</div>
  if (!data) return <div className={s.emptyArea}>暂无数据</div>

  const filtered = (data.companies || []).filter(
    (c) => c.taxpayer_name.includes(search) || c.taxpayer_id.includes(search)
  )

  return (
    <div className={s.container}>
      {/* 1. 概览 */}
      <div className={s.headerCard}>
        <div className={s.overviewItem}>
          <div className={s.ovIcon}><Users size={20} /></div>
          <div className={s.ovText}>
            <div className={s.ovLabel}>管理企业总数</div>
            <div className={s.ovValue}>{(data.companies || []).length} <span className={s.unit}>家</span></div>
          </div>
        </div>
        <div className={s.overviewItem}>
          <div className={s.ovIcon} style={{ backgroundColor: '#eff6ff', color: '#3b82f6' }}><Calendar size={20} /></div>
          <div className={s.ovText}>
            <div className={s.ovLabel}>数据统计截止</div>
            <div className={s.ovValue}>{data.overall_date || new Date().toISOString().slice(0, 10)}</div>
          </div>
        </div>
      </div>

      {/* 2. 数据更新区域（仅admin可见） */}
      {isAdmin && (
        <div className={s.updateSection}>
          <div className={s.updateHeader}>
            <div className={s.updateTitle}>
              <RefreshCw size={16} className={s.updateIcon} />
              数据更新
            </div>
          </div>
          <div className={s.updateContent}>
            {/* 1. 财务指标批量重算 */}
            <div className={s.updateItem}>
              <div className={s.updateInfo}>
                <span className={s.updateItemTitle}>财务指标批量重算</span>
                <span className={s.updateDesc}>
                  重新计算所有企业的25个财务指标（月度/季度/年度）
                </span>
              </div>
              <button
                onClick={handleRecalculateMetrics}
                disabled={updating.metrics}
                className={s.updateButton}
              >
                {updating.metrics ? '重算中...' : '开始重算'}
              </button>
            </div>

            {/* 2-5. 其他功能 - 仅 sys 可见 */}
            {isSys && (
              <>
                {/* 2. 参考数据重载 */}
                <div className={s.updateItem}>
                  <div className={s.updateInfo}>
                    <span className={s.updateItemTitle}>参考数据重载</span>
                    <span className={s.updateDesc}>
                      重新加载同义词表、科目字典、指标定义等配置数据
                    </span>
                  </div>
                  <button
                    onClick={handleReloadReferenceData}
                    disabled={updating.reference}
                    className={s.updateButton}
                  >
                    {updating.reference ? '重载中...' : '开始重载'}
                  </button>
                </div>

                {/* 3. 数据质量批量检查 */}
                <div className={s.updateItem}>
                  <div className={s.updateInfo}>
                    <span className={s.updateItemTitle}>数据质量批量检查</span>
                    <span className={s.updateDesc}>
                      检查所有企业的数据一致性、合理性、完整性（5类检查）
                    </span>
                  </div>
                  <button
                    onClick={handleBatchQualityCheck}
                    disabled={updating.quality}
                    className={s.updateButton}
                  >
                    {updating.quality ? '检查中...' : '开始检查'}
                  </button>
                </div>

                {/* 4. 内存缓存清理 */}
                <div className={s.updateItem}>
                  <div className={s.updateInfo}>
                    <span className={s.updateItemTitle}>内存缓存清理</span>
                    <span className={s.updateDesc}>
                      清空查询缓存，确保使用最新数据（4层缓存：意图/SQL/结果/跨域）
                    </span>
                  </div>
                  <button
                    onClick={handleClearCache}
                    disabled={updating.cache}
                    className={s.updateButton}
                  >
                    {updating.cache ? '清理中...' : '开始清理'}
                  </button>
                </div>

                {/* 5. 配置热重载 */}
                <div className={s.updateItem}>
                  <div className={s.updateInfo}>
                    <span className={s.updateItemTitle}>配置热重载</span>
                    <span className={s.updateDesc}>
                      重新加载意图路由配置（tax_query_config.json），无需重启应用
                    </span>
                  </div>
                  <button
                    onClick={handleReloadConfig}
                    disabled={updating.config}
                    className={s.updateButton}
                  >
                    {updating.config ? '重载中...' : '开始重载'}
                  </button>
                </div>
              </>
            )}

            {/* 更新结果提示 */}
            {updateResult && (
              <div className={`${s.updateResult} ${updateResult.success ? s.success : s.error}`}>
                <span className={s.resultIcon}>{updateResult.success ? '✓' : '✗'}</span>
                <span className={s.resultMessage}>{updateResult.message}</span>
                {updateResult.details && (
                  <div className={s.resultDetails}>
                    {Object.entries(updateResult.details).map(([key, value]) => (
                      <div key={key}>{key}: {value}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. 操作区 */}
      <div className={s.toolbar}>
        <div className={s.searchBox}>
          <Search size={16} className={s.searchIcon} />
          <input
            className={s.searchInput}
            placeholder="通过企业名称或税号快速搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className={s.toolActions}>
          <button className={s.btnAction}><Filter size={14} /> 筛选条件</button>
          <button className={s.btnPrimary}><Download size={14} /> 导出报表</button>
        </div>
      </div>

      {/* 4. 企业列表（带滚动条） */}
      <div className={s.tableCard}>
        <div className={s.tableWrapper}>
          <table className={s.companyTable}>
            <thead>
              <tr>
                <th>企业基本信息</th>
                <th>数据同步状态</th>
                <th>最后更新时间</th>
                <th>完整度</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.taxpayer_id}>
                  <td>
                    <div className={s.companyInfo}>
                      <div className={s.companyAvatar}><Building2 size={16} /></div>
                      <div>
                        <div className={s.companyName}>{c.taxpayer_name}</div>
                        <div className={s.companyTax}>{c.taxpayer_id}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`${s.statusBadge} ${c.data_status === '已同步' ? s.stOk : s.stWait}`}>
                      {c.data_status}
                    </span>
                  </td>
                  <td><span className={s.dateText}>{c.last_update}</span></td>
                  <td>
                    <div className={s.progressWrapper}>
                      <div className={s.progressLabel}>{c.completeness || '95%'}</div>
                      <div className={s.progressBar}>
                        <div className={s.progressFill} style={{ width: c.completeness || '95%' }} />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className={s.emptyTable}>没有找到符合条件的单位</div>}
      </div>
    </div>
  )
}
