import { useState, useEffect } from 'react'
import s from './CompanyProfile.module.css'
import { fetchProfile, fetchReports } from '../../services/api'
import { AlertCircle, FileText, RefreshCw, X } from 'lucide-react'
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

export default function CompanyProfile({ selectedCompanyId, onGenerateReport, onViewReports }) {
  const [year, setYear] = useState(2025)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [existingReport, setExistingReport] = useState(null)

  useEffect(() => {
    if (!selectedCompanyId) return
    setLoading(true)
    setError(null)
    fetchProfile(selectedCompanyId, year)
      .then((d) => { setData(d); setError(null) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedCompanyId, year])

  const handleGenerateReport = async () => {
    if (!onGenerateReport || !data) return

    try {
      const res = await fetchReports(selectedCompanyId, 1, 100)
      const existing = res.items?.find((r) => Number(r.year) === Number(year))
      if (existing) {
        setExistingReport(existing)
        setShowConfirmModal(true)
        return
      }
    } catch (e) {
      console.error('Failed to check existing reports:', e)
    }

    onGenerateReport({
      mode: 'generate',
      taxpayerId: selectedCompanyId,
      taxpayerName: data.basic_info?.taxpayer_name || selectedCompanyId,
      year,
    })
  }

  const confirmRegenerate = () => {
    setShowConfirmModal(false)
    onGenerateReport({
      mode: 'generate',
      taxpayerId: selectedCompanyId,
      taxpayerName: data.basic_info?.taxpayer_name || selectedCompanyId,
      year,
    })
  }

  const confirmView = () => {
    setShowConfirmModal(false)
    if (existingReport) {
      onGenerateReport({ mode: 'view', reportId: existingReport.id, taxpayerName: existingReport.taxpayer_name, year: existingReport.year })
    }
  }

  const handleViewReports = () => {
    if (onViewReports) {
      onViewReports()
    }
  }

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
        onGenerateReport={handleGenerateReport}
        onViewReports={handleViewReports}
      />
      <div className={s.moduleGrid}>
        <ProfileSection title="企业身份" index={0} defaultOpen>
          <IdentityModule data={data.basic_info} />
        </ProfileSection>

        <ProfileSection title="股权与治理" index={1} defaultOpen>
          <ShareholderModule data={data} />
        </ProfileSection>

        <ProfileSection title="组织与人力" index={2} defaultOpen>
          <HRModule data={data} />
        </ProfileSection>

        <ProfileSection title="财务表现" index={3} defaultOpen>
          <FinancialModule data={data} />
        </ProfileSection>

        <ProfileSection title="业务运营" index={4}>
          <BusinessModule data={data} />
        </ProfileSection>

        <ProfileSection title="研发创新" index={5}>
          <RDModule data={data} />
        </ProfileSection>

        <ProfileSection title="税务表现" index={6}>
          <TaxModule data={data} />
        </ProfileSection>

        <ProfileSection title="跨境业务" index={7} defaultOpen={false}>
          <CrossBorderModule data={data} />
        </ProfileSection>

        <ProfileSection title="合规风险" index={8} defaultOpen={false}>
          <ComplianceModule data={data} />
        </ProfileSection>

        <ProfileSection title="外部关系" index={9} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="数字化" index={10} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="ESG表现" index={11} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="政策匹配" index={12} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
        <ProfileSection title="特殊业务" index={13} defaultOpen={false}>
          <PlaceholderModule />
        </ProfileSection>
      </div>

      {showConfirmModal && existingReport && (
        <div className={s.modalOverlay}>
          <div className={s.modalContent}>
            <div className={s.modalTitle}>
              <AlertCircle size={20} color="var(--color-warning)" />
              提示：报告已存在
            </div>
            <div className={s.modalBody}>
              发现该企业 <strong>{year} </strong> 年度的分析报告已存在（状态：{existingReport.status === 'completed' ? '已完成' : existingReport.status}）。
              生成报告耗时较长，您可以直接查看现有报告，或选择作为新记录重新生成。
            </div>
            <div className={s.modalActions}>
              <button className={s.btnCancel} onClick={() => setShowConfirmModal(false)}>
                <X size={14} /> 取消
              </button>
              <button className={s.btnView} onClick={confirmView}>
                <FileText size={14} /> 查看报告
              </button>
              <button className={s.btnRegenerate} onClick={confirmRegenerate}>
                <RefreshCw size={14} /> 重新生成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
