import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import s from '../CompanyProfile.module.css'

export default function ComplianceModule({ data }) {
  const risk = data?.compliance_risk

  return (
    <div className={s.subGrid5}>
      <div className={s.subCard}>
        <SectionTitle name="税务合规" color="green" />
        <CompactMetric label="申报及时率" value="100%"
          evalData={{ level: '优秀', type: 'positive' }} />
        <CompactMetric label="缴款及时率" value="100%"
          evalData={{ level: '优秀', type: 'positive' }} />
        <CompactMetric label="稽查次数" value="0次"
          evalData={{ level: '良好', type: 'positive' }} />
        <CompactMetric label="税务风险等级" value="低"
          evalData={{ level: '良好', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="财务合规" color="purple" />
        <CompactMetric label="审计意见" value="标准无保留意见"
          evalData={{ level: '优秀', type: 'positive' }} />
        <CompactMetric label="会计规范性" value="优"
          evalData={{ level: '优', type: 'positive' }} />
        <CompactMetric label="内控缺陷" value="0个"
          evalData={{ level: '良好', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="法律风险" color="orange" />
        <CompactMetric label="涉诉案件" value="0件"
          evalData={{ level: '无', type: 'positive' }} />
        <CompactMetric label="失信被执行" value="0次"
          evalData={{ level: '良好', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="经营合规" color="cyan" />
        <CompactMetric label="经营异常" value="0次" />
        <CompactMetric label="质量处罚" value="0条"
          evalData={{ level: '良好', type: 'positive' }} />
        <CompactMetric label="环保处罚" value="—"
          evalData={{ level: '中', type: 'neutral' }} />
        <CompactMetric label="安全事故" value="—"
          evalData={{ level: '低', type: 'positive' }} />
      </div>
      <div className={s.subCard}>
        <SectionTitle name="风险评估" color="blue" />
        <CompactMetric label="流动性风险" value={risk?.liquidity_eval?.level || '低'}
          evalData={risk?.liquidity_eval || { level: '安全', type: 'positive' }} />
        <CompactMetric label="供应商依赖" value="低"
          evalData={{ level: '低', type: 'positive' }} />
        <CompactMetric label="客户集中风险" value="低"
          evalData={{ level: '低', type: 'positive' }} />
        <CompactMetric label="综合评级" value="—"
          evalData={{ level: '良好', type: 'positive' }} />
      </div>
    </div>
  )
}
