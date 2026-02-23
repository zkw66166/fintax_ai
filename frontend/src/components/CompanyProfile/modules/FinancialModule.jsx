import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import ProgressBar from '../ProgressBar'
import MiniChart from '../MiniChart'
import { fmtAmount, fmtPct, fmtGrowth } from '../utils'
import s from '../CompanyProfile.module.css'

export default function FinancialModule({ data }) {
  const asset = data?.asset_structure
  const profit = data?.profit_data
  const cf = data?.cash_flow
  const growth = data?.growth_metrics
  const metrics = data?.financial_metrics

  return (
    <div>
      {/* Row 1: 综合能力 + 资产结构 + 负债权益 */}
      <div className={s.subGrid3}>
        <CapabilityCard metrics={metrics} profit={profit} asset={asset} cf={cf} growth={growth} />
        <AssetCard asset={asset} growth={growth} />
        <LiabilityCard asset={asset} />
      </div>
      {/* Row 2: 盈利 + 偿债 + 运营 + 成长 */}
      <div className={s.subGrid4} style={{ borderTop: '1px solid #f0f0f0' }}>
        <ProfitCard profit={profit} growth={growth} />
        <SolvencyCard asset={asset} metrics={metrics} />
        <EfficiencyCard metrics={metrics} />
        <GrowthCard growth={growth} />
      </div>
      {/* Row 3: 费用 + 现金流 */}
      <div className={s.subGrid2} style={{ borderTop: '1px solid #f0f0f0' }}>
        <ExpenseCard profit={profit} />
        <CashFlowCard cf={cf} />
      </div>
    </div>
  )
}

function CapabilityCard({ metrics, profit, asset, cf, growth }) {
  const nm = profit?.net_margin || 0
  const dr = asset?.debt_ratio || 0
  const rg = growth?.revenue_growth?.rate || 0
  const opCf = cf?.operating || 0

  const scores = [
    { label: '现金流', pct: opCf > 0 ? 100 : 40, color: 'blue' },
    { label: '所有者权益', pct: Math.min(Math.round(100 - dr * 0.64), 100), color: 'blue' },
    { label: '盈利能力', pct: Math.min(Math.round(nm * 10 + 40), 100), color: 'blue' },
    { label: '偿债能力', pct: Math.min(Math.round(100 - dr), 100), color: 'blue' },
    { label: '运营效率', pct: 90, color: 'blue' },
  ]
  const totalScore = ((nm * 2 + (100 - dr) * 0.5 + rg * 0.5 + 40) / 100 * 100).toFixed(1)

  return (
    <div className={s.subCard}>
      <SectionTitle name="财务综合能力" color="green" />
      <CompactMetric label="综合评分" value={`${(dr || 35.8).toFixed(1)}%`}
        evalData={{ level: '稳健', type: 'positive' }} />
      {scores.map(sc => (
        <ProgressBar key={sc.label} label={sc.label} percent={sc.pct} color={sc.color} />
      ))}
      <CompactMetric label="综合能力得分" value={`${totalScore}分`}
        evalData={{ level: '优秀', type: 'positive' }} />
    </div>
  )
}

function AssetCard({ asset, growth }) {
  if (!asset) return <div className={s.subCard}><SectionTitle name="资产结构分析" color="blue" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  const assetGrowth = growth?.asset_growth
  return (
    <div className={s.subCard}>
      <SectionTitle name="资产结构分析" color="blue" />
      <CompactMetric label="资产总额" value={fmtAmount(asset.total_assets)}
        suffix={assetGrowth?.rate != null ? fmtGrowth(assetGrowth) : null} />
      <CompactMetric label="流动资产" value={fmtAmount(asset.current_assets)} />
      <CompactMetric label="固定资产" value={fmtAmount(asset.fixed_assets)} />
      <MiniChart type="bar" labels={['流动资产', '固定资产', '无形资产']}
        datasets={[{
          data: [asset.current_assets || 0, asset.fixed_assets || 0, asset.intangible_assets || 0],
          backgroundColor: ['#1677ff', '#36cfc9', '#597ef7'],
        }]} height={140} />
    </div>
  )
}

function LiabilityCard({ asset }) {
  if (!asset) return <div className={s.subCard}><SectionTitle name="负债与权益" color="purple" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  return (
    <div className={s.subCard}>
      <SectionTitle name="负债与权益" color="purple" />
      <CompactMetric label="资产负债率" value={fmtPct(asset.debt_ratio)} evalData={asset.debt_ratio_eval} />
      <MiniChart type="bar" labels={['负债', '所有者权益']}
        datasets={[{
          data: [asset.total_liabilities || 0, asset.total_equity || 0],
          backgroundColor: ['#faad14', '#52c41a'],
        }]} height={140} />
    </div>
  )
}

function ProfitCard({ profit, growth }) {
  if (!profit) return <div className={s.subCard}><SectionTitle name="盈利能力" color="cyan" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  const revGrowth = fmtGrowth(growth?.revenue_growth)
  return (
    <div className={s.subCard}>
      <SectionTitle name="盈利能力" color="cyan" />
      <CompactMetric label="营业收入" value={fmtAmount(profit.revenue)}
        suffix={revGrowth} evalData={growth?.revenue_growth?.eval} />
      <CompactMetric label="毛利率" value={fmtPct(profit.gross_margin)} evalData={profit.gross_margin_eval} />
      <CompactMetric label="净利润" value={fmtAmount(profit.net_profit)} />
      <CompactMetric label="净利率" value={fmtPct(profit.net_margin)} evalData={profit.net_margin_eval} />
    </div>
  )
}

function SolvencyCard({ asset, metrics }) {
  const items = metrics?.['偿债能力'] || []
  const find = (code) => items.find(i => i.code === code)
  const cr = find('current_ratio')
  const qr = find('quick_ratio')
  return (
    <div className={s.subCard}>
      <SectionTitle name="偿债能力" color="green" />
      <CompactMetric label="资产负债率" value={fmtPct(asset?.debt_ratio)}
        evalData={asset?.debt_ratio_eval} />
      <CompactMetric label="流动比率" value={cr?.value != null ? cr.value.toFixed(2) : '—'}
        evalData={cr?.eval_level ? { level: cr.eval_level, type: 'positive' } : null} />
      <CompactMetric label="速动比率" value={qr?.value != null ? qr.value.toFixed(2) : '—'}
        evalData={qr?.eval_level ? { level: qr.eval_level, type: 'positive' } : null} />
    </div>
  )
}

function EfficiencyCard({ metrics }) {
  const items = metrics?.['营运能力'] || []
  const find = (code) => items.find(i => i.code === code)
  const ar = find('ar_turnover')
  const at = find('asset_turnover') || find('total_asset_turnover')
  const arDays = ar?.value ? (365 / ar.value).toFixed(0) : '—'
  return (
    <div className={s.subCard}>
      <SectionTitle name="运营效率" color="purple" />
      <CompactMetric label="应收款周转天数" value={arDays} unit="天" />
      <CompactMetric label="应收款周转率" value={ar?.value != null ? `${ar.value.toFixed(2)}次` : '—'} />
      <CompactMetric label="总资产周转率" value={at?.value != null ? `${at.value.toFixed(2)}次` : '—'} />
    </div>
  )
}

function GrowthCard({ growth }) {
  if (!growth) return <div className={s.subCard}><SectionTitle name="成长能力" color="orange" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  return (
    <div className={s.subCard}>
      <SectionTitle name="成长能力" color="orange" />
      <CompactMetric label="资产增长率" value={fmtGrowth(growth.asset_growth) || '—'}
        evalData={growth.asset_growth?.eval} />
      <CompactMetric label="营收增长率" value={fmtGrowth(growth.revenue_growth) || '—'}
        evalData={growth.revenue_growth?.eval} />
      <CompactMetric label="净利润增长率" value={fmtGrowth(growth.net_profit_growth) || '—'}
        evalData={growth.net_profit_growth?.eval} />
    </div>
  )
}

function ExpenseCard({ profit }) {
  if (!profit) return <div className={s.subCard}><SectionTitle name="成本费用结构" color="cyan" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  return (
    <div className={s.subCard}>
      <SectionTitle name="成本费用结构" color="cyan" />
      <CompactMetric label="销售费用" value={fmtAmount(profit.selling_expense)}
        suffix={profit.selling_expense_rate != null ? `费用率 ${fmtPct(profit.selling_expense_rate)}` : null} />
      <CompactMetric label="管理费用" value={fmtAmount(profit.admin_expense)}
        suffix={profit.admin_expense_rate != null ? `费用率 ${fmtPct(profit.admin_expense_rate)}` : null} />
      <CompactMetric label="研发费用" value={fmtAmount(profit.rd_expense)} />
      <CompactMetric label="财务费用" value={fmtAmount(profit.financial_expense)} />
    </div>
  )
}

function CashFlowCard({ cf }) {
  if (!cf) return <div className={s.subCard}><SectionTitle name="现金流量" color="blue" /><span style={{color:'#999',fontSize:13}}>暂无数据</span></div>
  return (
    <div className={s.subCard}>
      <SectionTitle name="现金流量" color="blue" />
      <CompactMetric label="经营活动现金流" value={fmtAmount(cf.operating)} evalData={cf.operating_eval} />
      <CompactMetric label="投资活动现金流" value={fmtAmount(cf.investing)} />
      <CompactMetric label="筹资活动现金流" value={fmtAmount(cf.financing)} />
    </div>
  )
}
