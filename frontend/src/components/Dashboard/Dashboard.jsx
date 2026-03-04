import { useState, useEffect } from 'react'
import s from './Dashboard.module.css'
import HealthScorecard from './widgets/HealthScorecard'
import TaxBurdenSummary from './widgets/TaxBurdenSummary'
import DataQualityAlert from './widgets/DataQualityAlert'
import QuickQueryShortcuts from './widgets/QuickQueryShortcuts'
import RecentQueries from './widgets/RecentQueries'
import ClientPortfolio from './widgets/ClientPortfolio'

export default function Dashboard({ selectedCompanyId, onPageChange, onQueryClick, onCompanyChange, user }) {
  const [companyName, setCompanyName] = useState('')

  useEffect(() => {
    if (selectedCompanyId) {
      fetchCompanyName(selectedCompanyId)
    }
  }, [selectedCompanyId])

  const fetchCompanyName = async (companyId) => {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/companies', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const companies = await response.json()
        const company = companies.find(c => c.taxpayer_id === companyId)
        if (company) {
          setCompanyName(company.taxpayer_name || company.company_name)
        }
      }
    } catch (err) {
      console.error('Failed to fetch company name:', err)
    }
  }

  const handleQueryClick = (query) => {
    if (onQueryClick) {
      onQueryClick(query)
    }
    if (onPageChange) {
      onPageChange('chat')
    }
  }

  const handleCompanySelect = (companyId) => {
    if (onCompanyChange) {
      onCompanyChange(companyId)
    }
  }

  const isMultiCompanyUser = user?.role === 'firm' || user?.role === 'group' || user?.role === 'admin' || user?.role === 'sys'

  return (
    <div className={s.dashboard}>
      <div className={s.header}>
        <h1 className={s.title}>工作台</h1>
        <p className={s.subtitle}>
          {companyName ? `当前公司: ${companyName}` : '欢迎使用财税智能咨询系统'}
        </p>
      </div>

      <div className={s.grid}>
        {isMultiCompanyUser ? (
          <>
            {/* Multi-company layout for firm/group/admin users */}
            <ClientPortfolio onCompanySelect={handleCompanySelect} onPageChange={onPageChange} />
            <HealthScorecard companyId={selectedCompanyId} onNavigate={onPageChange} />
            <TaxBurdenSummary companyId={selectedCompanyId} />
            <DataQualityAlert companyId={selectedCompanyId} />
            <QuickQueryShortcuts
              companyId={selectedCompanyId}
              companyName={companyName}
              onQueryClick={handleQueryClick}
            />
            <RecentQueries onQueryClick={handleQueryClick} />
          </>
        ) : (
          <>
            {/* Single-company layout for enterprise users */}
            <HealthScorecard companyId={selectedCompanyId} onNavigate={onPageChange} />
            <TaxBurdenSummary companyId={selectedCompanyId} />
            <DataQualityAlert companyId={selectedCompanyId} />
            <QuickQueryShortcuts
              companyId={selectedCompanyId}
              companyName={companyName}
              onQueryClick={handleQueryClick}
            />
            <RecentQueries onQueryClick={handleQueryClick} />
          </>
        )}
      </div>
    </div>
  )
}
