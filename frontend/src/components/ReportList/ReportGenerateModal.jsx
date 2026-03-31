import { useState, useEffect } from 'react'
import { Building2, Calendar, X, Loader2, AlertCircle, FileText, RefreshCw } from 'lucide-react'
import { fetchCompanies, fetchReports } from '../../services/api'
import s from './ReportGenerateModal.module.css'

const YEARS = [2025, 2024, 2023]

export default function ReportGenerateModal({ onClose, onGenerate, defaultCompanyId }) {
  const [companies, setCompanies] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCompany, setSelectedCompany] = useState('')
  const [selectedYear, setSelectedYear] = useState(2025)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [existingReport, setExistingReport] = useState(null)

  useEffect(() => {
    fetchCompanies()
      .then((data) => {
        if (Array.isArray(data)) {
          setCompanies(data)
          if (defaultCompanyId) {
            setSelectedCompany(defaultCompanyId)
          }
        } else if (data.items) {
          setCompanies(data.items)
          if (defaultCompanyId) {
            setSelectedCompany(defaultCompanyId)
          }
        } else {
          setCompanies([])
        }
      })
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false))
  }, [defaultCompanyId])

  const handleGenerate = async () => {
    if (!selectedCompany) {
      alert('请选择企业')
      return
    }
    const company = companies.find((c) => c.taxpayer_id === selectedCompany || c.id === selectedCompany)
    const taxpayerName = company?.taxpayer_name || company?.name || selectedCompany

    try {
      const res = await fetchReports(selectedCompany, 1, 100)
      const existing = res.items?.find((r) => Number(r.year) === Number(selectedYear))
      if (existing) {
        setExistingReport(existing)
        setShowConfirmModal(true)
        return
      }
    } catch (e) {
      console.error('Failed to check existing reports:', e)
    }

    onGenerate({
      mode: 'generate',
      taxpayerId: selectedCompany,
      taxpayerName,
      year: selectedYear,
    })
    onClose()
  }

  const confirmRegenerate = () => {
    setShowConfirmModal(false)
    const company = companies.find((c) => c.taxpayer_id === selectedCompany || c.id === selectedCompany)
    onGenerate({
      mode: 'generate',
      taxpayerId: selectedCompany,
      taxpayerName: company?.taxpayer_name || company?.name || selectedCompany,
      year: selectedYear,
    })
    onClose()
  }

  const confirmView = () => {
    setShowConfirmModal(false)
    if (existingReport) {
      onGenerate({
        mode: 'view',
        reportId: existingReport.id,
        taxpayerName: existingReport.taxpayer_name,
        year: existingReport.year,
      })
      onClose()
    }
  }

  return (
    <>
      <div className={s.overlay} onClick={onClose}>
        <div className={s.modal} onClick={(e) => e.stopPropagation()}>
          <div className={s.header}>
            <h3 className={s.title}>生成分析报告</h3>
            <button className={s.closeBtn} onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <div className={s.body}>
            <div className={s.field}>
              <label className={s.label}>
                <Building2 size={14} />
                选择企业
              </label>
              {loading ? (
                <div className={s.loading}>
                  <Loader2 size={16} className={s.spin} /> 加载中...
                </div>
              ) : (
                <select
                  className={s.select}
                  value={selectedCompany}
                  onChange={(e) => setSelectedCompany(e.target.value)}
                >
                  <option value="">请选择企业</option>
                  {companies.map((c) => (
                    <option key={c.taxpayer_id || c.id} value={c.taxpayer_id || c.id}>
                      {c.taxpayer_name || c.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className={s.field}>
              <label className={s.label}>
                <Calendar size={14} />
                选择年度
              </label>
              <select
                className={s.select}
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>{y}年度</option>
                ))}
              </select>
            </div>
          </div>

          <div className={s.footer}>
            <button className={s.cancelBtn} onClick={onClose}>
              取消
            </button>
            <button className={s.generateBtn} onClick={handleGenerate} disabled={!selectedCompany}>
              生成报告
            </button>
          </div>
        </div>
      </div>

      {showConfirmModal && existingReport && (
        <div className={s.confirmOverlay}>
          <div className={s.confirmModal}>
            <div className={s.confirmTitle}>
              <AlertCircle size={20} color="var(--color-warning)" />
              提示：报告已存在
            </div>
            <div className={s.confirmBody}>
              发现该企业 <strong>{selectedYear}</strong> 年度的分析报告已存在（状态：{existingReport.status === 'completed' ? '已完成' : existingReport.status}）。
              生成报告耗时较长，您可以直接查看现有报告，或选择作为新记录重新生成。
            </div>
            <div className={s.confirmActions}>
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
    </>
  )
}