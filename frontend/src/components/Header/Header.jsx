import { useState, useEffect } from 'react'
import s from './Header.module.css'

export default function Header({ selectedCompanyId, onCompanyChange }) {
  const [time, setTime] = useState(new Date())
  const [companies, setCompanies] = useState([])

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    fetch('/api/companies')
      .then((r) => r.json())
      .then((list) => {
        setCompanies(list)
        if (list.length > 0 && !selectedCompanyId) {
          onCompanyChange(list[0].taxpayer_id)
        }
      })
      .catch(() => {})
  }, [])

  const fmt = (d) => {
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }

  return (
    <header className={s.header}>
      <div className={s.logo}>
        <span className={s.logoIcon}>💼</span>
        <div>
          <div className={s.logoTitle}>智能财税咨询系统</div>
          <div className={s.logoSub}>ENTERPRISE FINANCIAL &amp; TAX INTELLIGENCE PLATFORM</div>
        </div>
      </div>

      <select
        className={s.companySelect}
        value={selectedCompanyId}
        onChange={(e) => onCompanyChange(e.target.value)}
      >
        {companies.length === 0 && <option>加载中...</option>}
        {companies.map((c) => (
          <option key={c.taxpayer_id} value={c.taxpayer_id}>
            {c.taxpayer_name}
          </option>
        ))}
      </select>

      <div className={s.rightInfo}>
        <span className={s.clock}>{fmt(time)}</span>
        <span className={s.bell}>🔔<span className={s.badge}>3</span></span>
        <div className={s.user}>
          <span className={s.userName}>超级管理员</span>
          <span className={s.userRole}>企业用户</span>
        </div>
        <span className={s.logout} title="退出登录">⏻</span>
      </div>
    </header>
  )
}
