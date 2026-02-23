import { useState, useEffect } from 'react'
import s from './CompanyProfile.module.css'
import { fetchProfile } from '../../services/api'
import ProfileHeader from './ProfileHeader'
import ProfileSection from './ProfileSection'
import IdentityModule from './modules/IdentityModule'
import ShareholderModule from './modules/ShareholderModule'
import HRModule from './modules/HRModule'
import FinancialModule from './modules/FinancialModule'
import BusinessModule from './modules/BusinessModule'
import RDModule from './modules/RDModule'
import TaxModule from './modules/TaxModule'
import CrossBorderModule from './modules/CrossBorderModule'
import ComplianceModule from './modules/ComplianceModule'
import PlaceholderModule from './modules/PlaceholderModule'

export default function CompanyProfile({ selectedCompanyId }) {
  const [year, setYear] = useState(2025)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!selectedCompanyId) return
    setLoading(true)
    setError(null)
    fetchProfile(selectedCompanyId, year)
      .then((d) => { setData(d); setError(null) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedCompanyId, year])

  if (!selectedCompanyId) {
    return <div className={s.stateWrap}>请先在顶部选择企业</div>
  }
  if (loading) {
    return <div className={s.stateWrap}><span className={s.spinner} /> 加载企业画像...</div>
  }
  if (error) {
    return <div className={s.stateWrap}>加载失败: {error}</div>
  }
  if (!data || data.error) {
    return <div className={s.stateWrap}>{data?.error || '暂无数据'}</div>
  }
  return (
    <div className={s.profilePage}>
      <ProfileHeader
        companyName={data.basic_info?.taxpayer_name}
        creditCode={data.basic_info?.taxpayer_id}
        year={year}
        onYearChange={setYear}
      />
      <div className={s.moduleGrid}>
        <ProfileSection title="企业身份画像" index={0} defaultOpen>
          <IdentityModule data={data.basic_info} />
        </ProfileSection>

        <ProfileSection title="股权与治理画像" index={1} defaultOpen>
          <ShareholderModule data={data} />
        </ProfileSection>

        <ProfileSection title="组织与人力画像" index={2} defaultOpen>
          <HRModule data={data} />
        </ProfileSection>

        <ProfileSection title="财务画像" index={3} defaultOpen>
          <FinancialModule data={data} />
        </ProfileSection>

        <ProfileSection title="业务运营画像" index={4}>
          <BusinessModule data={data} />
        </ProfileSection>

        <ProfileSection title="研发创新画像" index={5}>
          <RDModule data={data} />
        </ProfileSection>

        <ProfileSection title="税务画像" index={6}>
          <TaxModule data={data} />
        </ProfileSection>

        <ProfileSection title="跨境业务画像" index={7} defaultOpen={false}>
          <CrossBorderModule data={data} />
        </ProfileSection>

        <ProfileSection title="合规风险画像" index={8} defaultOpen={false}>
          <ComplianceModule data={data} />
        </ProfileSection>

        <ProfileSection title="外部关系画像" index={9} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="数字化画像" index={10} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="ESG画像" index={11} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="政策匹配画像" index={12} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="特殊业务画像" index={13} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
      </div>
    </div>
  )
}
