import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import ResultTable from '../ResultTable/ResultTable'
import ChartRenderer from '../ChartRenderer/ChartRenderer'
import GrowthTable from '../GrowthTable/GrowthTable'
import PipelineDetail from '../PipelineDetail/PipelineDetail'
import s from './ChatMessage.module.css'

const ROUTE_CONFIG = {
  financial_data: { label: '📊 财务数据查询', cls: s.routeFinancial },
  tax_incentive: { label: '📋 本地知识库查询结果', cls: s.routeTax },
  regulation: { label: '🤖 法规知识库', cls: s.routeRegulation },
}

export default function ChatMessage({ msg, interpretation, isSelectionMode, isSelected, onToggleSelect, questionText }) {
  const [copied, setCopied] = useState(false)
  const copyToClipboard = async (text, e) => {
    e?.stopPropagation()
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
    } catch (_) {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      try { document.execCommand('copy') } catch (_) {}
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  const checkbox = isSelectionMode && (
    <label className={s.selectWrap} onClick={(e) => e.stopPropagation()}>
      <input
        type="checkbox"
        className={s.selectCheckbox}
        checked={isSelected}
        onChange={onToggleSelect}
      />
    </label>
  )

  if (msg.role === 'user') {
    return (
      <div className={s.userMsg} style={isSelectionMode ? { display: 'flex', gap: 8 } : undefined}>
        {checkbox}
        <div>
          <div className={s.userTs}>[{msg.ts || new Date().toLocaleTimeString()}] 您</div>
          {msg.content}
        </div>
      </div>
    )
  }

  const rc = ROUTE_CONFIG[msg.route] || ROUTE_CONFIG.financial_data
  const isStreaming = msg.status === 'streaming'
  const isDone = msg.status === 'done'
  const dd = msg.result?.display_data
  const mode = msg.responseMode || 'detailed'
  // concise: text summary only; standard: table+growth, no chart; detailed: everything
  const showTable = mode !== 'concise'
  const showChart = mode === 'detailed'
  const showGrowth = mode !== 'concise'

  // Memoize growth chart data to avoid rebuilding on every render
  const growthChartData = useMemo(() => {
    if (!showChart || !dd?.growth) return null
    return buildGrowthChartData(dd.growth)
  }, [showChart, dd?.growth])

  const canCopy = msg.status === 'done' || msg.status === 'error'

  const buildCopyText = () => {
    const q = questionText ? `问题：${questionText}` : ''
    const parts = []
    if (q) parts.push(q)
    const answer = buildAnswerText(msg)
    if (answer) parts.push(`回答：${answer}`)
    if (interpretation?.text) parts.push(`数据解读：${interpretation.text}`)
    return parts.join('\n\n')
  }

  const handleCopy = (e) => {
    if (!canCopy) return
    const text = buildCopyText()
    copyToClipboard(text, e)
  }

  return (
    <div className={s.aiMsg} style={isSelectionMode ? { display: 'flex', gap: 8 } : undefined}>
      {checkbox}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className={s.aiLabel}>智能体:</div>
        <span className={`${s.routeBadge} ${rc.cls}`}>{rc.label}</span>
        {msg.cacheHit && <span className={s.cacheBadge}>缓存结果</span>}

        {/* Loading state */}
        {msg.status === 'loading' && (
          <div className={s.loading}>
            <span className={s.dot} />
            <span className={s.dot} />
            <span className={s.dot} />
            {msg.stageText && <span className={s.stageText}>{msg.stageText}</span>}
          </div>
        )}

        {/* Streaming text (tax_incentive / regulation) */}
        {isStreaming && msg.chunks && (
          <div className={s.content}>
            <ReactMarkdown>{msg.chunks.join('')}</ReactMarkdown>
            <span className={s.cursor} />
          </div>
        )}

        {/* Concise mode: multi-level fallback */}
        {isDone && mode === 'concise' && (
          <div className={s.content}>
            {dd?.summary ? (
              <p>{dd.summary}</p>
            ) : dd?.display_type === 'metric' ? (
              <MetricDisplay metrics={dd.metric_display} />
            ) : dd?.display_type === 'kv' ? (
              <KVDisplay table={dd.table} />
            ) : dd?.display_type === 'table' && dd.table?.rows?.length > 0 ? (
              <p>
                查询成功，共 {dd.table.rows.length} 条记录。
                {dd.table.headers.slice(0, 4).map((h) => `${h}: ${dd.table.rows[0][h] ?? '-'}`).join('；')}
                {dd.table.headers.length > 4 ? '…' : ''}
              </p>
            ) : dd?.display_type === 'cross_domain' && dd.sub_tables ? (
              <p>
                {dd.sub_tables.map((st) => st.domain_cn).join(' vs ')} 对比查询完成，
                共 {dd.sub_tables.reduce((n, st) => n + (st.table?.rows?.length || 0), 0)} 条记录。
              </p>
            ) : msg.content ? (
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            ) : (
              <p>查询完成</p>
            )}
          </div>
        )}

        {/* Done: financial_data with display_data (non-concise) */}
        {isDone && dd && dd.display_type === 'metric' && showTable && (
          <div className={s.content}>
            <MetricDisplay metrics={dd.metric_display} />
          </div>
        )}

        {isDone && dd && dd.display_type === 'kv' && showTable && (
          <div className={s.content}>
            <KVDisplay table={dd.table} />
          </div>
        )}

        {isDone && dd && dd.display_type === 'table' && showTable && (
          <div className={s.content}>
            <ResultTable displayData={dd.table} rowCount={msg.result?.results?.length} />
            {showChart && dd.chart_data && <ChartRenderer chartData={dd.chart_data} />}
            {showGrowth && dd.growth && <GrowthTable growth={dd.growth} />}
            {growthChartData && <ChartRenderer chartData={growthChartData} />}
          </div>
        )}

        {isDone && dd && dd.display_type === 'cross_domain' && showTable && (
          <div className={s.content}>
            {dd.summary && <div className={s.summary}>{dd.summary}</div>}
            {dd.sub_tables ? (
              dd.sub_tables.map((st, i) => (
                <SubDomainSection key={i} st={st} showChart={showChart} showGrowth={showGrowth} />
              ))
            ) : (
              <>
                <ResultTable displayData={dd.table} rowCount={msg.result?.results?.length} />
                {showChart && dd.chart_data && <ChartRenderer chartData={dd.chart_data} />}
                {showGrowth && dd.growth && <GrowthTable growth={dd.growth} />}
                {showChart && dd.growth && (() => { const g = buildGrowthChartData(dd.growth); return g && <ChartRenderer chartData={g} /> })()}
              </>
            )}
          </div>
        )}
        {/* Done: no display_data, fallback to raw results */}
        {isDone && !dd && msg.result?.results && showTable && (
          <div className={s.content}>
            {msg.result.results.length > 0 ? (
              <ResultTable results={msg.result.results} />
            ) : msg.content ? (
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            ) : (
              <p className={s.emptyState}>查询完成，当前条件下无数据。请检查查询期间或导入相关数据。</p>
            )}
          </div>
        )}

        {/* Done: text-based routes or clarification/error */}
        {isDone && !msg.result?.results && !dd && msg.content && (
          <div className={s.content}>
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}

        {/* Done: result count for tax_incentive */}
        {isDone && msg.route === 'tax_incentive' && msg.result?.result_count != null && (
          <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>
            找到 {msg.result.result_count} 条相关政策
          </div>
        )}

        {/* Error */}
        {msg.status === 'error' && <div className={s.errorMsg}>{msg.content || '查询失败'}</div>}

        {/* Data interpretation */}
        {isDone && mode !== 'concise' && interpretation && (interpretation.text || interpretation.status === 'streaming') && (
          <InterpretationSection interpretation={interpretation} />
        )}

        {/* Pipeline detail for financial_data */}
        {isDone && msg.pipelineDetail && <PipelineDetail detail={msg.pipelineDetail} />}

        <div className={s.copyRow}>
          <button className={s.copyBtn} onClick={handleCopy} disabled={!canCopy}>
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </div>
    </div>
  )
}

function buildAnswerText(msg) {
  if (!msg) return ''
  if (msg.content) return msg.content
  if (msg.status === 'error') return msg.content || '查询失败'
  const dd = msg.result?.display_data
  if (!dd) return ''
  if (dd.summary) return dd.summary
  if (dd.display_type === 'metric' && dd.metric_display) {
    return dd.metric_display.map((m) => `${m.label}: ${m.formatted_value}`).join('\n')
  }
  if (dd.display_type === 'kv' && dd.table) {
    return tableToText(dd.table)
  }
  if (dd.display_type === 'table' && dd.table) {
    return tableToText(dd.table)
  }
  if (dd.display_type === 'cross_domain' && dd.sub_tables) {
    return dd.sub_tables.map((st) => `${st.domain_cn}\n${tableToText(st.table)}`).join('\n\n')
  }
  if (dd.table) return tableToText(dd.table)
  return ''
}

function tableToText(table) {
  if (!table || !table.headers || !table.rows) return ''
  const header = table.headers.join('\t')
  const rows = table.rows.map((row) => table.headers.map((h) => row[h] ?? '').join('\t'))
  return [header, ...rows].join('\n')
}


function MetricDisplay({ metrics }) {
  if (!metrics || metrics.length === 0) return null
  return (
    <div>
      {metrics.map((m, i) => (
        <div key={i} className={s.metricItem}>
          <span className={s.metricLabel}>{m.label}：</span>
          <span className={s.metricValue}>{m.formatted_value}</span>
          {m.sources && Object.keys(m.sources).length > 0 && (
            <div className={s.metricSources}>
              计算依据：{Object.entries(m.sources).map(([k, v]) => `${k}=${v}`).join('，')}
            </div>
          )}
          {m.error && <div className={s.metricError}>{m.error}</div>}
        </div>
      ))}
    </div>
  )
}


function KVDisplay({ table }) {
  if (!table || !table.headers || !table.rows || table.rows.length === 0) return null
  const row = table.rows[0]
  return (
    <div className={s.kvList}>
      {table.headers.map((h) => {
        const val = row[h]
        if (val == null || val === '' || val === '-') return null
        return (
          <div key={h} className={s.kvItem}>
            <span className={s.kvLabel}>{h}</span>
            <span className={s.kvValue}>{val}</span>
          </div>
        )
      })}
    </div>
  )
}


function SubDomainSection({ st, showChart, showGrowth }) {
  const growthChart = useMemo(() => {
    if (!showChart || !st.growth) return null
    return buildGrowthChartData(st.growth)
  }, [showChart, st.growth])

  return (
    <div className={s.subDomain}>
      <div className={s.subDomainTitle}>{st.domain_cn}</div>
      <ResultTable displayData={st.table} />
      {showChart && st.chart_data && <ChartRenderer chartData={st.chart_data} />}
      {showGrowth && st.growth && <GrowthTable growth={st.growth} />}
      {growthChart && <ChartRenderer chartData={growthChart} />}
    </div>
  )
}


function InterpretationSection({ interpretation }) {
  if (!interpretation) return null
  return (
    <div className={s.interpretSection}>
      <div className={s.interpretHeader}>
        <span className={s.interpretTitle}>数据解读</span>
        {interpretation.status === 'streaming' && (
          <span className={s.interpretLoading}>分析中...</span>
        )}
      </div>
      {interpretation.status === 'error' && (
        <div className={s.interpretError}>数据解读暂时不可用</div>
      )}
      {interpretation.text && (
        <div className={s.interpretContent}>
          <ReactMarkdown>{interpretation.text}</ReactMarkdown>
          {interpretation.status === 'streaming' && <span className={s.cursor} />}
        </div>
      )}
    </div>
  )
}


const GROWTH_COLORS = [
  'rgba(54, 162, 235, 0.8)',
  'rgba(255, 99, 132, 0.8)',
  'rgba(75, 192, 192, 0.8)',
  'rgba(255, 206, 86, 0.8)',
  'rgba(153, 102, 255, 0.8)',
  'rgba(255, 159, 64, 0.8)',
]

function buildGrowthChartData(growth) {
  if (!growth || growth.length < 1) return null

  const labels = growth.map((g) => g.period)
  const metricNames = []
  for (const entry of growth) {
    for (const key of Object.keys(entry)) {
      if (key !== 'period' && !metricNames.includes(key)) metricNames.push(key)
    }
  }
  if (metricNames.length === 0) return null

  const datasets = metricNames.slice(0, 6).map((name, idx) => ({
    label: `${name} 变动率`,
    data: growth.map((g) => g[name]?.change_pct ?? null),
    type: 'bar',
    backgroundColor: GROWTH_COLORS[idx % GROWTH_COLORS.length],
    borderColor: GROWTH_COLORS[idx % GROWTH_COLORS.length].replace('0.8', '1'),
    borderWidth: 1,
    borderRadius: 4,
    yAxisID: 'y',
  }))

  return {
    chartType: 'bar',
    title: '环比变动率趋势分析',
    labels,
    datasets,
    percentageY: true,
  }
}
