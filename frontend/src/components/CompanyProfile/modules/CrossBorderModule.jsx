import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import { fmtAmount, fmtPct } from '../utils'
import s from '../CompanyProfile.module.css'

export default function CrossBorderModule({ data }) {
  const cb = data?.cross_border

  const ratio = cb?.foreign_income_ratio
  const ratioEval = ratio != null
    ? ratio >= 20 ? { level: '大量', type: 'growth' }
    : ratio >= 5 ? { level: '少量', type: 'positive' }
    : { level: '极少', type: 'neutral' }
    : null

  return (
    <div className={s.subGrid3}>
      <div className={s.subCard}>
        <SectionTitle name="跨境交易" color="green" />
        <CompactMetric label="境外收入总额" value={fmtAmount(cb?.foreign_income)} />
        <CompactMetric label="境外收入占比" value={fmtPct(ratio)} evalData={ratioEval} />
        <CompactMetric label="出口销售额" value={fmtAmount(cb?.foreign_income)} />
        <CompactMetric label="进口采购额" value="—" />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="关联交易" color="purple" />
        <CompactMetric label="关联交易总额" value="0万元" />
        <CompactMetric label="关联交易定价" value="可比非受控价格法"
          evalData={{ level: '合规', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="国际税收" color="orange" />
        <CompactMetric label="适用税收协定" value="中关税收协定" />
        <CompactMetric label="境外已缴税款" value={fmtAmount(cb?.foreign_tax_due)} />
        <CompactMetric label="境外税收抵免" value={fmtAmount(cb?.foreign_tax_credit)}
          evalData={cb?.foreign_tax_credit ? { level: '已免', type: 'positive' } : null} />
      </div>
    </div>
  )
}
