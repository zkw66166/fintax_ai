import s from './ProfileHeader.module.css'

const YEARS = [2025, 2024, 2023]

export default function ProfileHeader({ companyName, creditCode, year, onYearChange }) {
  return (
    <div className={s.header}>
      <h1 className={s.name}>{companyName || '—'}</h1>
      <div className={s.meta}>
        {creditCode && <span className={s.creditCode}>{creditCode}</span>}
        <span className={s.sep}>|</span>
        <select className={s.yearSelect} value={year} onChange={(e) => onYearChange(Number(e.target.value))}>
          {YEARS.map((y) => <option key={y} value={y}>{y}年刷新数据</option>)}
        </select>
      </div>
    </div>
  )
}
