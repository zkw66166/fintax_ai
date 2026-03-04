import { useState, useEffect } from 'react'
import s from './SingleCompanyData.module.css'
import MonoTable from './shared/MonoTable'
import { fetchStats, runQualityCheck, recalculateMetrics } from '../../services/dataManagementApi'
import useAuth from '../../hooks/useAuth'
import {
  CheckCircle2, AlertCircle, XCircle, Search, Play,
  UploadCloud, ChevronRight, ChevronDown, BarChart3,
  Database, LineChart, FileCheck, RefreshCw
} from 'lucide-react'

const CATEGORY_NAMES = {
  internal_consistency: '表内勾稽',
  reasonableness: '合理性检查',
  cross_table: '跨表校验',
  period_continuity: '期间连续性',
  completeness: '完整性检查',
}

function QualityCheckPanel({ result }) {
  const [expandedDomains, setExpandedDomains] = useState({})
  if (!result || !result.summary) {
    return (
      <div className={s.qcPlaceholder}>
        点击"开始检测"按钮，对当前企业的财务报表数据进行全面勾稽检查。
        <br />
        检查范围：表内勾稽、合理性检查、跨表校验、期间连续性、完整性检查。
      </div>
    )
  }

  const { summary, domains } = result
  const toggleDomain = (domain) =>
    setExpandedDomains((prev) => ({ ...prev, [domain]: !prev[domain] }))

  return (
    <div className={s.qcPanel}>
      <div className={s.qcSummaryBar}>
        <div className={s.summaryItem}>
          <span className={s.totalChecks}>共 {summary.total_checks} 项</span>
        </div>
        <div className={s.summaryItem}>
          <CheckCircle2 size={14} className={s.qcPass} />
          <span className={s.qcPass}>通过 {summary.passed}</span>
        </div>
        <div className={s.summaryItem}>
          <XCircle size={14} className={s.qcFail} />
          <span className={s.qcFail}>失败 {summary.failed}</span>
        </div>
        <div className={s.summaryItem}>
          <AlertCircle size={14} className={s.qcWarn} />
          <span className={s.qcWarn}>警告 {summary.warned}</span>
        </div>
        <div className={s.qcRate}>通过率 {summary.pass_rate}%</div>
      </div>

      {Object.entries(summary.by_category || {}).map(([cat, catData]) => (
        <div key={cat} className={s.qcCategory}>
          <div className={s.qcCatHeader}>
            <span className={s.qcCatName}>{CATEGORY_NAMES[cat] || cat}</span>
            <span className={s.qcCatStats}>
              {catData.passed}/{catData.total} 通过
              {catData.failed > 0 && <span className={s.qcFail}> {catData.failed} 失败</span>}
              {catData.warned > 0 && <span className={s.qcWarn}> {catData.warned} 警告</span>}
            </span>
          </div>
          <div className={s.qcDomains}>
            {(domains || [])
              .filter((d) =>
                d.details.some((r) => r.category === cat) ||
                (d.details.length === 0 &&
                  cat === 'internal_consistency' &&
                  ['account_balance', 'balance_sheet', 'income_statement', 'cash_flow', 'vat_return', 'eit_return', 'invoice'].includes(d.domain))
              )
              .map((d) => {
                const catDetails = d.details.filter((r) => r.category === cat)
                const hasFail = catDetails.some((r) => r.status === 'fail')
                const hasWarn = catDetails.some((r) => r.status === 'warn')
                const isExpanded = expandedDomains[`${cat}-${d.domain}`]
                return (
                  <div key={d.domain} className={s.qcDomain}>
                    <div
                      className={s.qcDomainHeader}
                      onClick={() => toggleDomain(`${cat}-${d.domain}`)}
                    >
                      {hasFail ? <XCircle size={14} className={s.qcIconFail} /> :
                        hasWarn ? <AlertCircle size={14} className={s.qcIconWarn} /> :
                          <CheckCircle2 size={14} className={s.qcIconPass} />}
                      <span className={s.qcDomainName}>{d.domain_name_cn}</span>
                      {catDetails.length > 0 && (
                        <span className={s.qcDomainCount}>{catDetails.length} 项异常</span>
                      )}
                      <span className={s.qcArrow}>
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </span>
                    </div>
                    {isExpanded && catDetails.length > 0 && (
                      <div className={s.qcDetails}>
                        {catDetails.map((r, i) => (
                          <div key={i} className={`${s.qcDetail} ${r.status === 'fail' ? s.qcDetailFail : r.status === 'warn' ? s.qcDetailWarn : ''}`}>
                            <span className={s.qcRuleId}>{r.rule_id}</span>
                            <span className={s.qcRuleName}>{r.rule_name_cn}</span>
                            <span className={s.qcPeriod}>{r.period}</span>
                            {r.expected != null && (
                              <div className={s.qcValues}>
                                <span>预期: <b className={s.num}>{r.expected?.toLocaleString()}</b></span>
                                <span>实际: <b className={s.num}>{r.actual?.toLocaleString()}</b></span>
                                <span>差异: <b className={s.numDif}>{r.difference?.toLocaleString()}</b></span>
                              </div>
                            )}
                            {r.message && <div className={s.qcMsg}>{r.message}</div>}
                          </div>
                        ))}
                      </div>
                    )}
                    {isExpanded && catDetails.length === 0 && (
                      <div className={s.qcDetails}>
                        <div className={s.qcAllPass}>全部检验通过，未发现异常数据。</div>
                      </div>
                    )}
                  </div>
                )
              })}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function SingleCompanyData({ selectedCompanyId }) {
  const { isAdmin } = useAuth()
  const [stats, setStats] = useState(null)
  const [checkResult, setCheckResult] = useState(null)
  const [checkError, setCheckError] = useState(null)
  const [checking, setChecking] = useState(false)
  const [loading, setLoading] = useState(true)
  const [recalculating, setRecalculating] = useState(false)
  const [recalcResult, setRecalcResult] = useState(null)

  useEffect(() => {
    if (!selectedCompanyId) return
    setLoading(true)
    fetchStats(selectedCompanyId)
      .then(setStats)
      .catch(() => { })
      .finally(() => setLoading(false))
  }, [selectedCompanyId])

  const handleCheck = async () => {
    setChecking(true)
    setCheckError(null)
    try {
      const res = await runQualityCheck(selectedCompanyId)
      setCheckResult(res)
    } catch (err) {
      setCheckError(err.message || '质量检查请求失败，请稍后重试')
    }
    setChecking(false)
  }

  const handleRecalculate = async () => {
    if (!selectedCompanyId) {
      alert('请先选择企业')
      return
    }

    if (!confirm('确认重新计算该企业的财务指标？\n\n此操作将覆盖现有指标数据，耗时约3-5秒。')) {
      return
    }

    setRecalculating(true)
    setRecalcResult(null)

    try {
      const result = await recalculateMetrics(selectedCompanyId, 'both')
      setRecalcResult(result)

      // 3秒后自动刷新统计数据
      setTimeout(() => {
        fetchStats(selectedCompanyId).then(setStats).catch(() => {})
      }, 3000)
    } catch (error) {
      setRecalcResult({
        success: false,
        message: error.message || '重算失败'
      })
    } finally {
      setRecalculating(false)
    }
  }

  if (loading) return <div className={s.loadingArea}><div className={s.spinner}></div>加载中...</div>
  if (!stats) return <div className={s.emptyArea}>暂无数据</div>

  const overviewItems = [
    { value: stats.metric_count, label: '财务指标数量', icon: BarChart3, color: '#3b82f6' },
    { value: stats.data_entry_count, label: '报表/数据条目', icon: Database, color: '#8b5cf6' },
    { value: `${stats.period_continuity_pct}%`, label: '数据期间(月)连续性', icon: LineChart, color: '#10b981' },
    { value: `${stats.data_completeness_pct}%`, label: '数据完整度评价', icon: FileCheck, color: '#f59e0b' },
  ]

  const mappingCols = [
    { key: 'standard_name', label: '标准指标名称', align: 'left' },
    { key: 'synonyms', label: '识别同义词', align: 'left' },
    { key: 'status', label: '状态', align: 'left' },
    { key: 'match_rate', label: '匹配度', align: 'right' },
  ]
  const mappingRows = (stats.synonym_mappings || []).map((m) => ({
    ...m,
    match_rate: m.match_rate != null ? `${m.match_rate}%` : '',
  }))

  const freqCols = [
    { key: 'source', label: '数据源', align: 'left' },
    { key: 'frequency', label: '更新频率', align: 'left' },
    { key: 'last_update', label: '上次更新', align: 'left' },
    { key: 'status', label: '状态', align: 'left' },
  ]

  return (
    <div className={s.container}>
      {/* 1. 核心数据概览 */}
      <div className={s.overview}>
        {overviewItems.map((item, i) => {
          const Icon = item.icon
          return (
            <div key={i} className={s.overviewCard}>
              <div className={s.cardHeader}>
                <div className={s.cardIcon} style={{ backgroundColor: item.color + '15', color: item.color }}>
                  <Icon size={20} />
                </div>
              </div>
              <div className={s.cardBody}>
                <div className={s.overviewValue}>{item.value}</div>
                <div className={s.overviewLabel}>{item.label}</div>
              </div>
            </div>
          )
        })}
      </div>

      <div className={s.grid}>
        {/* 2. 智能数据映射 */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <div className={s.sectionTitle}>
              <Search size={16} className={s.titleIcon} /> 智能数据映射 (指标同义词库)
            </div>
          </div>
          <div className={s.sectionContent}>
            <MonoTable columns={mappingCols} rows={mappingRows} />
          </div>
        </div>

        {/* 4. 数据更新频率 */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <div className={s.sectionTitle}>
              <ClockIcon size={16} className={s.titleIcon} /> 数据实时更新频率
            </div>
          </div>
          <div className={s.sectionContent}>
            <MonoTable columns={freqCols} rows={stats.update_frequency || []} />
          </div>
        </div>
      </div>

      {/* 3. 数据质量检查 */}
      <div className={s.section}>
        <div className={s.sectionHeader}>
          <div className={s.sectionTitle}>
            <FileCheck size={16} className={s.titleIcon} /> 数据质量勾稽检查报告
          </div>
          <div className={s.headerActions}>
            {checkResult && checkResult.gaap_type && (
              <span className={s.qcGaap}>{checkResult.gaap_type}</span>
            )}
            <button className={`${s.btn} ${checking ? s.btnLoading : ''}`} onClick={handleCheck} disabled={checking}>
              {checking ? '检测中...' : <><Play size={14} fill="currentColor" /> 开始检测</>}
            </button>
          </div>
        </div>
        <div className={s.sectionContent}>
          {checkError && (
            <div className={s.qcError}>
              <AlertCircle size={14} /> {checkError}
            </div>
          )}
          <QualityCheckPanel result={checkResult} />
        </div>
      </div>

      {/* 4. 数据更新区域（仅admin可见） */}
      {isAdmin && (
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <div className={s.sectionTitle}>
              <RefreshCw size={16} className={s.titleIcon} /> 数据更新
            </div>
          </div>
          <div className={s.sectionContent}>
            <div className={s.updatePanel}>
              <div className={s.updateItem}>
                <div className={s.updateInfo}>
                  <h4>财务指标重算</h4>
                  <p className={s.updateDesc}>
                    重新计算该企业的所有财务指标（盈利能力、偿债能力、营运能力、成长能力、税负率等）
                  </p>
                  <p className={s.updateNote}>
                    ⚠️ 适用场景：修改了财务报表、VAT、EIT或发票数据后
                  </p>
                </div>

                <button
                  className={s.recalcButton}
                  onClick={handleRecalculate}
                  disabled={recalculating || !selectedCompanyId}
                >
                  {recalculating ? (
                    <>
                      <RefreshCw className={s.spinning} />
                      计算中...
                    </>
                  ) : (
                    <>
                      <RefreshCw />
                      开始重算
                    </>
                  )}
                </button>
              </div>

              {/* 结果提示 */}
              {recalcResult && (
                <div className={
                  recalcResult.success
                    ? s.resultSuccess
                    : s.resultError
                }>
                  <p>{recalcResult.message}</p>
                  {recalcResult.success && recalcResult.details && (
                    <p className={s.resultDetails}>
                      v1指标: {recalcResult.details.v1_count} 条 |
                      v2指标: {recalcResult.details.v2_count} 条 |
                      耗时: {(recalcResult.details.duration_ms / 1000).toFixed(2)}秒
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className={s.grid}>
        {/* 5. 数据使用统计 */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <div className={s.sectionTitle}>
              <BarChart3 size={16} className={s.titleIcon} /> 数据使用热度统计
            </div>
          </div>
          <div className={s.sectionContent}>
            <div className={s.usageGrid}>
              <div className={s.usageStat}>
                <div className={s.usageValue}>1,245</div>
                <div className={s.usageLabel}>本月查询次数</div>
              </div>
              <div className={s.usageStat}>
                <div className={s.usageValue}>56</div>
                <div className={s.usageLabel}>生成报告数</div>
              </div>
              <div className={s.usageStat}>
                <div className={s.usageValue}>8,932</div>
                <div className={s.usageLabel}>API调用量</div>
              </div>
              <div className={s.usageStat}>
                <div className={s.usageLabel}>长期使用趋势</div>
                <div className={s.usageTrend}>稳定增长</div>
              </div>
            </div>
          </div>
        </div>

        {/* 6. 智能数据导入 */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <div className={s.sectionTitle}>
              <UploadCloud size={16} className={s.titleIcon} /> 智能数据批量导入
            </div>
            <span className={s.demoTag}>Demo Only</span>
          </div>
          <div className={s.sectionContent}>
            <div className={s.uploadArea}>
              <UploadCloud size={32} className={s.uploadIcon} />
              <div className={s.uploadText}>点击或拖拽文件到此处录入</div>
              <div className={s.uploadHint}>支持 Excel (xlsx/xls), PDF, 扫描件 (OCR)</div>
              <button className={s.btnSecondary}>选择本地文件</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ClockIcon({ size, className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  )
}
