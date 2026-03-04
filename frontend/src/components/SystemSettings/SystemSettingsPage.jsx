import { useState } from 'react'
import s from './SystemSettingsPage.module.css'
import UserManagement from './UserManagement'
import BasicSettings from './BasicSettings'
import ServiceSettings from './ServiceSettings'
import { Users, Settings, Wrench } from 'lucide-react'

const TABS = [
  { key: 'user-management', label: '用户管理', icon: Users },
  { key: 'basic', label: '基础设置', icon: Settings },
  { key: 'service', label: '服务设置', icon: Wrench },
]

export default function SystemSettingsPage({ currentUser }) {
  const [activeTab, setActiveTab] = useState('user-management')

  return (
    <div className={s.page}>
      <div className={s.tabBar}>
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <div
              key={tab.key}
              className={`${s.tab} ${isActive ? s.tabActive : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <Icon size={16} strokeWidth={2.5} className={s.tabIcon} />
              {tab.label}
              {isActive && <div className={s.activeLine} />}
            </div>
          )
        })}
      </div>
      <div className={s.tabContent}>
        {activeTab === 'user-management' && (
          <UserManagement currentUser={currentUser} />
        )}
        {activeTab === 'basic' && <BasicSettings currentUser={currentUser} />}
        {activeTab === 'service' && <ServiceSettings currentUser={currentUser} />}
      </div>
    </div>
  )
}
