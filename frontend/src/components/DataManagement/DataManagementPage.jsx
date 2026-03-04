import { useState } from 'react'
import s from './DataManagementPage.module.css'
import SingleCompanyData from './SingleCompanyData'
import MultiCompanyData from './MultiCompanyData'
import DataBrowser from './DataBrowser'
import { Database, Users, Search } from 'lucide-react'

const TABS = [
  { key: 'single-company', label: '单户企业数据', icon: Database },
  { key: 'multi-company', label: '多户企业数据', icon: Users },
  { key: 'data-browser', label: '数据浏览', icon: Search },
]

export default function DataManagementPage({ selectedCompanyId }) {
  const [activeTab, setActiveTab] = useState('single-company')

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
        {activeTab === 'single-company' && <SingleCompanyData selectedCompanyId={selectedCompanyId} />}
        {activeTab === 'multi-company' && <MultiCompanyData />}
        {activeTab === 'data-browser' && <DataBrowser selectedCompanyId={selectedCompanyId} />}
      </div>
    </div>
  )
}
