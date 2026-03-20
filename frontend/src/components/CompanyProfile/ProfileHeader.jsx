import s from './ProfileHeader.module.css'
import { Building2, Calendar, FileText, History } from 'lucide-react'

const YEARS = [2025, 2024, 2023]

export default function ProfileHeader({ companyName, creditCode, year, onYearChange, onGenerateReport, onViewReports }) {
  return (
    <div className={s.headerCard}>
      <div className={s.iconWrap}>
        <Building2 size={24} className={s.icon} strokeWidth={1.5} />
      </div>
      <div className={s.infoPart}>
        <h1 className={s.name}>{companyName || '—'}</h1>
        <div className={s.meta}>
          {creditCode && <span className={s.creditCode}>统一社会信用代码：{creditCode}</span>}
        </div>
      </div>
      <div className={s.actionPart}>
        <button className={s.reportBtn} onClick={onGenerateReport} title="生成分析报告">
          <FileText size={14} /> 生成报告
        </button>
        <button className={s.reportListBtn} onClick={onViewReports} title="查看历史报告">
          <History size={14} /> 查看报告
        </button>
        <div className={s.yearControl}>
          <Calendar size={14} className={s.yearIcon} />
          <select className={s.yearSelect} value={year} onChange={(e) => onYearChange(Number(e.target.value))}>
            {YEARS.map((y) => <option key={y} value={y}>{y}年度全景洞察</option>)}
          </select>
        </div>
      </div>
    </div>
  )
}
