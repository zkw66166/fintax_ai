import s from './Sidebar.module.css'

const MENU = [
  { icon: '🏠', label: '工作台', disabled: true },
  { icon: '💬', label: 'AI智问', key: 'chat' },
  { icon: '🏢', label: '企业画像', key: 'profile' },
  { icon: '📊', label: '数据管理', disabled: true },
  { icon: '⚙️', label: '系统设置', disabled: true },
]

export default function Sidebar({ currentPage, onPageChange }) {
  return (
    <nav className={s.sidebar}>
      {MENU.map((m) => (
        <div
          key={m.label}
          className={`${s.item} ${m.key === currentPage ? s.active : ''} ${m.disabled ? s.disabled : ''}`}
          onClick={() => m.key && !m.disabled && onPageChange(m.key)}
          style={{ cursor: m.key && !m.disabled ? 'pointer' : 'default' }}
        >
          <span className={s.icon}>{m.icon}</span>
          {m.label}
        </div>
      ))}
    </nav>
  )
}
