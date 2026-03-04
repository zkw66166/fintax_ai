import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import MiniChart from '../MiniChart'
import { fmtAmount, fmtPct } from '../utils'
import s from '../CompanyProfile.module.css'

export default function TaxModule({ data }) {
  const basic = data?.basic_info
  const tax = data?.tax_summary
  const metrics = data?.financial_metrics

  const taxBurdenItems = metrics?.['税负率类'] || []
  const totalBurden = taxBurdenItems.find(i => i.code === 'total_tax_burden')

  return (
    <div className={s.subGrid3}>
      <div className={s.subCard}>
        <SectionTitle name="纳税人信息" color="green" />
        <CompactMetric label="纳税人识别号" value={basic?.taxpayer_id} />
        <CompactMetric label="纳税人类型" value={basic?.taxpayer_type || '一般纳税人'}
          evalData={{ level: '正常', type: 'positive' }} />
        <CompactMetric label="征收方式" value={basic?.collection_method || '查账征收'} />
        <CompactMetric label="纳税信用等级" value={basic?.credit_grade_current}
          evalData={{ level: '优秀', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="综合税负" color="blue" />
        <CompactMetric label="年度纳税总额" value={fmtAmount(tax?.tax_total)} />
        <CompactMetric label="综合税负率"
          value={totalBurden?.value != null ? fmtPct(totalBurden.value) : '—'}
          evalData={{ level: '合理', type: 'positive' }} />
        <CompactMetric label="增值税额" value={fmtAmount(tax?.vat_total)} />
        <CompactMetric label="企业所得税" value={fmtAmount(tax?.eit_total)} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="税种构成" color="purple" />
        <MiniChart type="bar"
          labels={['增值税', '企业所得税']}
          datasets={[{
            data: [tax?.vat_total || 0, tax?.eit_total || 0],
            backgroundColor: ['#93c5fd', '#c4b5fd'],
          }]}
          height={180} />
      </div>
    </div>
  )
}
