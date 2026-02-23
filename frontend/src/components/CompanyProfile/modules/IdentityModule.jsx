import CompactMetric from '../CompactMetric'
import SectionTitle from '../SectionTitle'
import s from '../CompanyProfile.module.css'

export default function IdentityModule({ data }) {
  if (!data) return null

  const truncate = (str, len = 20) => {
    if (!str) return '—'
    return str.length > len ? str.substring(0, len) + '...' : str
  }

  return (
    <div className={s.subGrid4}>
      {/* 基本工商信息 */}
      <div className={s.subCard}>
        <SectionTitle name="基本工商信息" color="green" />
        <CompactMetric label="统一社会信用代码" value={data.taxpayer_id} />
        <CompactMetric label="企业类型" value={data.company_type || data.registration_type} />
        <CompactMetric label="法定代表人" value={data.legal_representative} />
        <CompactMetric label="成立日期" value={data.established_date || data.establish_date} />
        <CompactMetric label="经营状态" value={data.operating_status || data.status || '存续'}
          evalData={{ level: '正常', type: 'positive' }} />
        <CompactMetric label="注册地址" value={truncate(data.registered_address)} />
      </div>

      {/* 规模特征 */}
      <div className={s.subCard}>
        <SectionTitle name="规模特征" color="purple" />
        <CompactMetric label="注册资本" value={data.registered_capital}
          evalData={{ level: '充足', type: 'positive' }} />
        <CompactMetric label="员工人数" value={data.insured_count != null ? `${data.insured_count}人` : '—'} />
      </div>

      {/* 行业定位 */}
      <div className={s.subCard}>
        <SectionTitle name="行业定位" color="orange" />
        <CompactMetric label="所属行业" value={data.industry_name || data.industry} />
        <CompactMetric label="产业链位置" value="核心环节"
          evalData={{ level: '核心环节', type: 'positive' }} />
      </div>

      {/* 资质认证 */}
      <div className={s.subCard}>
        <SectionTitle name="资质认证" color="blue" />
        <CompactMetric label="纳税人资格" value={data.taxpayer_type || '一般纳税人'} />
        <CompactMetric label="纳税信用等级" value={data.credit_grade_current}
          evalData={data.credit_grade_current === 'A' ? { level: '优秀', type: 'positive' } :
                    data.credit_grade_current === 'B' ? { level: '良好', type: 'positive' } : null} />
        <CompactMetric label="会计准则" value={data.accounting_standard} />
        <CompactMetric label="征收方式" value={data.collection_method} />
      </div>
    </div>
  )
}
