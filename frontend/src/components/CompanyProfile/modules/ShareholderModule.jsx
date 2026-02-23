import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import MiniChart from '../MiniChart'
import { fmtAmount } from '../utils'
import s from '../CompanyProfile.module.css'

export default function ShareholderModule({ data }) {
  const sh = data?.shareholders
  if (!sh) return <div style={{ padding: '16px 0', textAlign: 'center', color: '#999', fontSize: 13 }}>暂无股权数据</div>

  const holders = sh.shareholders || []
  const pieLabels = holders.map(h => h.name)
  const pieData = holders.map(h => h.ratio)

  return (
    <div className={s.subGrid2}>
      <div className={s.subCard}>
        <SectionTitle name="股权信息" />
        <CompactMetric label="股东总数" value={`${sh.total_count}人`} />
        <CompactMetric label="最大股东" value={sh.top_shareholder}
          evalData={sh.is_controlling ? { level: '控股', type: 'positive' } : null} />
        <CompactMetric label="最大股东持股" value={sh.top_ratio != null ? `${sh.top_ratio}%` : '—'}
          evalData={sh.is_controlling ? { level: '控股', type: 'positive' } : null} />
        <CompactMetric label="分红总额" value={fmtAmount(sh.total_dividend)} />
        <CompactMetric label="对外投资数" value="0家" />
        {holders.length > 0 && (
          <MiniChart type="pie" labels={pieLabels}
            datasets={[{ data: pieData }]} height={180} />
        )}
      </div>
      <div className={s.subCard}>
        <SectionTitle name="公司治理" />
        <CompactMetric label="财务审计意见" value="标准无保留意见"
          evalData={{ level: '良好', type: 'positive' }} />
        <CompactMetric label="内控缺陷数" value="0个"
          evalData={{ level: '规范', type: 'positive' }} />
      </div>
    </div>
  )
}
