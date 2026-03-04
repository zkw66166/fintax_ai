import { useState, useEffect } from 'react'
import s from './DataBrowser.module.css'
import MonoTable from './shared/MonoTable'
import RawFormatView from './RawFormatView'
import { fetchBrowseTables, fetchBrowsePeriods, fetchBrowseData } from '../../services/dataManagementApi'
import { Filter, FileText, Calendar, Table, FileCode } from 'lucide-react'

const RAW_SUPPORTED = ['profit', 'balance_sheet', 'cash_flow', 'vat', 'eit_annual', 'eit_quarter']

export default function DataBrowser({ selectedCompanyId }) {
  const [tables, setTables] = useState([])
  const [periods, setPeriods] = useState([])
  const [selectedDomain, setSelectedDomain] = useState('')
  const [selectedPeriod, setSelectedPeriod] = useState('all')
  const [viewMode, setViewMode] = useState('general')
  const [tableData, setTableData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [companyName, setCompanyName] = useState('')

  // Load tables when company changes
  useEffect(() => {
    if (!selectedCompanyId) return
    fetchBrowseTables(selectedCompanyId).then((res) => {
      setTables(res.tables || res || [])
      if (res.company_name) setCompanyName(res.company_name)
      const list = res.tables || res || []
      if (list.length > 0 && !selectedDomain) {
        const defaultDomain = list.find((t) => t.key === 'profit')?.key || list[0].key
        setSelectedDomain(defaultDomain)
      }
    }).catch(() => { })
  }, [selectedCompanyId])

  // Load periods when domain changes
  useEffect(() => {
    if (!selectedCompanyId || !selectedDomain) return
    fetchBrowsePeriods(selectedCompanyId, selectedDomain).then((res) => {
      setPeriods(res || [])
      setSelectedPeriod('all')
    }).catch(() => setPeriods([]))
  }, [selectedCompanyId, selectedDomain])

  // Load data when filters change
  useEffect(() => {
    if (!selectedCompanyId || !selectedDomain) return
    // Raw format requires a specific period
    if (viewMode === 'raw' && selectedPeriod === 'all') {
      const firstSpecific = periods.find((p) => p.value !== 'all')
      if (firstSpecific) {
        setSelectedPeriod(firstSpecific.value)
        return
      }
    }
    setLoading(true)
    fetchBrowseData(selectedCompanyId, selectedDomain, selectedPeriod, viewMode)
      .then(setTableData)
      .catch(() => setTableData(null))
      .finally(() => setLoading(false))
  }, [selectedCompanyId, selectedDomain, selectedPeriod, viewMode])

  const handleDomainChange = (domain) => {
    setSelectedDomain(domain)
    if (!RAW_SUPPORTED.includes(domain)) setViewMode('general')
    else setViewMode('general')
    setTableData(null)
  }

  const handleViewModeChange = (mode) => {
    setViewMode(mode)
    if (mode === 'raw' && selectedPeriod === 'all') {
      const firstSpecific = periods.find((p) => p.value !== 'all')
      if (firstSpecific) setSelectedPeriod(firstSpecific.value)
    }
  }

  const domainLabel = tables.find((t) => t.key === selectedDomain)?.label || ''
  const showRawToggle = RAW_SUPPORTED.includes(selectedDomain)

  return (
    <div className={s.container}>
      {/* Filter bar */}
      <div className={s.filterCard}>
        <div className={s.filterGroup}>
          <div className={s.filterItem}>
            <span className={s.label}>
              <Filter size={14} className={s.labelIcon} /> 选择企业
            </span>
            <div className={s.staticValue}>{companyName || selectedCompanyId}</div>
          </div>

          <div className={s.filterItem}>
            <span className={s.label}>
              <FileText size={14} className={s.labelIcon} /> 选择数据表
            </span>
            <div className={s.selectWrapper}>
              <select
                className={s.select}
                value={selectedDomain}
                onChange={(e) => handleDomainChange(e.target.value)}
              >
                {tables.map((t) => (
                  <option key={t.key} value={t.key}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className={s.filterItem}>
            <span className={s.label}>
              <Calendar size={14} className={s.labelIcon} /> 选择期间
            </span>
            <div className={s.selectWrapper}>
              <select
                className={s.select}
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
              >
                {viewMode === 'general' && <option value="all">全部期间</option>}
                {periods.filter((p) => p.value !== 'all').map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className={s.toggleArea}>
          <div className={s.segmentedControl}>
            <button
              className={`${s.segmentBtn} ${viewMode === 'general' ? s.active : ''}`}
              onClick={() => handleViewModeChange('general')}
            >
              <Table size={14} /> 通表格式
            </button>
            {showRawToggle && (
              <button
                className={`${s.segmentBtn} ${viewMode === 'raw' ? s.active : ''}`}
                onClick={() => handleViewModeChange('raw')}
              >
                <FileCode size={14} /> 原表格式
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className={s.contentArea}>
        {loading ? (
          <div className={s.loadingState}>
            <div className={s.spinner}></div>
            加载中...
          </div>
        ) : viewMode === 'general' ? (
          <div className={s.generalView}>
            {tableData && tableData.columns ? (
              <>
                <div className={s.infoBar}>
                  <span className={s.badge}>{domainLabel}</span>
                  <span className={s.totalRows}>共 {tableData.total_rows} 条数据</span>
                </div>
                <MonoTable columns={tableData.columns} rows={tableData.rows || []} />
              </>
            ) : (
              <div className={s.emptyState}>暂无数据</div>
            )}
          </div>
        ) : (
          <div className={s.rawView}>
            {tableData ? (
              <RawFormatView data={tableData} />
            ) : (
              <div className={s.emptyState}>暂无数据</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
