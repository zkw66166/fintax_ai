import { useState, useEffect } from 'react'
import s from './Header.module.css'
import { Building2, Bell, User as UserIcon, LogOut, Clock } from 'lucide-react'

export default function Header({ selectedCompanyId, onCompanyChange, user, onLogout }) {
  const [time, setTime] = useState(new Date())
  const [companies, setCompanies] = useState([])

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const headers = {}
    const token = localStorage.getItem('access_token')
    if (token) headers.Authorization = `Bearer ${token}`
    fetch('/api/companies', { headers })
      .then((r) => r.json())
      .then((list) => {
        setCompanies(list)
        // Auto-select first company if none selected
        if (list.length > 0 && !selectedCompanyId) {
          console.log('Auto-selecting first company:', list[0].taxpayer_name)
          onCompanyChange(list[0].taxpayer_id)
        }
      })
      .catch((err) => {
        console.error('Failed to fetch companies:', err)
      })
  }, [selectedCompanyId, onCompanyChange])

  const fmt = (d) => {
    const pad = (n) => String(n).padStart(2, '0')
    const dateStr = `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`
    const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    return { dateStr, timeStr }
  }

  const { dateStr, timeStr } = fmt(time)

  const ROLE_LABELS = {
    sys: '超级管理员', admin: '系统管理员', firm: '事务所用户',
    group: '集团企业用户', enterprise: '普通企业用户',
  }
  const displayName = user?.display_name || user?.username || '用户'
  const roleLabel = ROLE_LABELS[user?.role] || '企业用户'

  return (
    <header className={s.header}>
      <div className={s.logoArea}>
        <div className={s.logo}>
          <div className={s.logoImg}>
            <BriefcaseFill />
          </div>
          <div className={s.logoText}>
            <div className={s.logoTitle}>智能财税咨询系统</div>
            <div className={s.logoSub}>ENTERPRISE FINANCIAL & TAX INTELLIGENCE PLATFORM</div>
          </div>
        </div>
      </div>

      <div className={s.centerArea}>
        <div className={s.companyBox}>
          <Building2 size={16} className={s.companyIcon} />
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
        </div>
      </div>

      <div className={s.rightArea}>
        <div className={s.timeDisplay}>
          <Clock size={14} />
          <span>{dateStr} {timeStr}</span>
        </div>

        <div className={s.actionIcons}>
          <div className={s.iconBtn}>
            <Bell size={18} />
            <span className={s.badge}>3</span>
          </div>
        </div>

        <div className={s.userProfile}>
          <div className={s.userInfo}>
            <div className={s.userName}>{displayName}</div>
            <div className={s.userRole}>{roleLabel}</div>
          </div>
          <div className={s.avatar}>
            <UserIcon size={20} />
          </div>
        </div>

        <button className={s.logoutBtn} onClick={onLogout} title="退出登录">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}

function BriefcaseFill() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20 7h-4V5c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm-10-2h4v2h-4V5z" />
    </svg>
  )
}
