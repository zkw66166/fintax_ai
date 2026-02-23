import { useMemo } from 'react'
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

export default function ChatMessage({ msg, isSelectionMode, isSelected, onToggleSelect }) {
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

  return (
    <div className={s.aiMsg} style={isSelectionMode ? { display: 'flex', gap: 8 } : undefined}>
      {checkbox}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className={s.aiLabel}>智能体:</div>
        <span className={`${s.routeBadge} ${rc.cls}`}>{rc.label}</span>

        {/* Loading state */}
        {msg.status === 'loading' && (
          <div className={s.loading}>
            <span className={s.dot} />
            <span className={s.dot} />
            <span className={s.dot} />
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
            <ResultTable results={msg.result.results} />
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

        {/* Pipeline detail for financial_data */}
        {isDone && msg.pipelineDetail && <PipelineDetail detail={msg.pipelineDetail} />}
      </div>
    </div>
  )
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
