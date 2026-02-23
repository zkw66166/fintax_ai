import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import MiniChart from '../MiniChart'
import s from '../CompanyProfile.module.css'

export default function HRModule({ data }) {
  const hr = data?.employee_structure
  if (!hr) return <div style={{ padding: '16px 0', textAlign: 'center', color: '#999', fontSize: 13 }}>暂无人力数据</div>

  const posDist = hr.position_dist || []
  const eduDist = hr.edu_dist || []

  const posLabels = posDist.map(p => `${p.type}人员`)
  const posData = posDist.map(p => p.count)

  const eduLabels = eduDist.map(e => e.education)
  const eduData = eduDist.map(e => e.count)

  // 本科及以上评价
  const bachelorEval = hr.bachelor_ratio >= 70
    ? { level: '优秀', type: 'positive' }
    : hr.bachelor_ratio >= 50
    ? { level: '良好', type: 'positive' }
    : { level: '一般', type: 'neutral' }

  return (
    <div className={s.subGrid3}>
      <div className={s.subCard}>
        <SectionTitle name="人员结构" />
        <CompactMetric label="员工总数" value={`${hr.total_employees}人`} />
        <CompactMetric label="研发人员数" value={`${hr.rd_count}人`} />
        <CompactMetric label="研发人员占比" value={`${hr.rd_ratio}%`} />
        <CompactMetric label="高新技术人员" value={`${hr.high_tech_count}人`}
          evalData={{ level: `${hr.high_tech_ratio}%`, type: 'positive' }} />
        {posLabels.length > 0 && (
          <MiniChart type="pie" labels={posLabels}
            datasets={[{ data: posData }]} height={180} />
        )}
      </div>
      <div className={s.subCard}>
        <SectionTitle name="学历结构分析" />
        <CompactMetric label="本科及以上占比" value={`${hr.bachelor_ratio}%`}
          evalData={bachelorEval} />
        <CompactMetric label="平均年龄" value={hr.avg_age != null ? `${hr.avg_age}岁` : '—'} />
        <CompactMetric label="平均工龄" value={hr.avg_work_years != null ? `${hr.avg_work_years}年` : '—'} />
        {eduLabels.length > 0 && (
          <MiniChart type="pie" labels={eduLabels}
            datasets={[{ data: eduData }]} height={180} />
        )}
      </div>
      <div className={s.subCard}>
        <SectionTitle name="人员概况" />
        <CompactMetric label="男性员工" value={`${hr.male_count}人`} />
        <CompactMetric label="女性员工" value={`${hr.female_count}人`} />
        <CompactMetric label="社保覆盖率" value="100%"
          evalData={{ level: '合规', type: 'positive' }} />
      </div>
    </div>
  )
}
