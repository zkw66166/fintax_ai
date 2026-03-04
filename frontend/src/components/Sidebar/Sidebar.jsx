import s from './Sidebar.module.css'
import { LayoutDashboard, MessageSquare, Briefcase, Database, Settings } from 'lucide-react'

const MENU = [
  { icon: LayoutDashboard, label: '工作台', key: 'dashboard' },
  { icon: MessageSquare, label: 'AI智问', key: 'chat' },
  { icon: Briefcase, label: '企业画像', key: 'profile' },
  { icon: Database, label: '数据管理', key: 'data-management' },
  { icon: Settings, label: '系统设置', key: 'settings' },
]

export default function Sidebar({ currentPage, onPageChange }) {
  return (
    <nav className={s.sidebar}>
      <div className={s.menuList}>
        {MENU.map((m) => {
          const Icon = m.icon
          const isActive = m.key === currentPage
          return (
            <div
              key={m.label}
              className={`${s.item} ${isActive ? s.active : ''} ${m.disabled ? s.disabled : ''}`}
              onClick={() => m.key && !m.disabled && onPageChange(m.key)}
              style={{ cursor: m.key && !m.disabled ? 'pointer' : 'default' }}
            >
              <Icon size={18} strokeWidth={2} className={s.icon} />
              <span className={s.label}>{m.label}</span>
            </div>
          )
        })}
      </div>
    </nav>
  )
}
