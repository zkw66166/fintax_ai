import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import ProgressBar from '../ProgressBar'
import MiniChart from '../MiniChart'
import { fmtAmount, fmtPct } from '../utils'
import s from '../CompanyProfile.module.css'

export default function RDModule({ data }) {
  const rd = data?.rd_innovation
  const rdExpense = rd?.rd_expense
  const rdIntensity = rd?.rd_intensity

  return (
    <div className={s.subGrid3}>
      <div className={s.subCard}>
        <SectionTitle name="研发投入" color="green" />
        <CompactMetric label="研发投入总额" value={fmtAmount(rdExpense)}
          evalData={rdExpense ? { level: '充足', type: 'positive' } : null} />
        <CompactMetric label="研发投入强度" value={fmtPct(rdIntensity)}
          evalData={rd?.rd_intensity_eval} />
        <CompactMetric label="研发人员占比" value="—" />
        <CompactMetric label="高新产品收入占比" value="—" />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="知识产权" color="purple" />
        <CompactMetric label="专利总数" value="—"
          evalData={{ level: '丰富', type: 'positive' }} />
        <CompactMetric label="发明专利" value="—"
          evalData={{ level: '活跃', type: 'positive' }} />
        <CompactMetric label="软件著作权" value="—" />
        <SectionTitle name="专利趋势" color="blue" />
        <MiniChart type="line"
          labels={['2022', '2023', '2024']}
          datasets={[{
            data: [0, 32, 15],
            borderColor: '#1677ff',
            pointBackgroundColor: '#1677ff',
          }]}
          height={120} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="研发成果" color="orange" />
        <CompactMetric label="发明专利占比" value="—" />
        <ProgressBar label="研发强度" percent={Math.min((rdIntensity || 0) * 10, 100)} color="blue" />
      </div>
    </div>
  )
}
