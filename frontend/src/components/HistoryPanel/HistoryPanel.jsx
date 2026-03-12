import { useState, useCallback, useEffect, useRef } from 'react'
import useChatHistory from '../../hooks/useChatHistory'
import Pagination from './Pagination'
import s from './HistoryPanel.module.css'

export default function HistoryPanel({ items, setItems, onSelect, onReinvoke, currentUser }) {
  const [selected, setSelected] = useState(new Set())
  const [searchText, setSearchText] = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [paginationData, setPaginationData] = useState({ total: 0, total_pages: 1 })
  const { removeEntries } = useChatHistory(items, setItems)
  const listRef = useRef(null)

  // Tab配置
  const tabs = [
    { id: 'all', label: '全部' },
    { id: 'financial_data', label: '财税数据' },
    { id: 'tax_incentive', label: '税收优惠' },
    { id: 'regulation', label: '法规知识' },
    { id: 'mixed_analysis', label: '综合分析' }
  ]

  // 检查是否可以删除（权限控制）
  const canDelete = useCallback((item) => {
    if (!currentUser) return false
    const userRole = currentUser.role || currentUser.user_role
    if (userRole === 'sys' || userRole === 'admin') return true
    return item.user_id === currentUser.id || item.user_id === currentUser.user_id
  }, [currentUser])

  // 从后端获取去重+分页数据
  const [filtered, setFiltered] = useState([])
  const [loading, setLoading] = useState(false)
  const [categoryCounts, setCategoryCounts] = useState({})

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          deduplicate: 'true',
          page: currentPage.toString(),
          page_size: '20'
        })
        if (activeTab !== 'all') {
          params.append('category', activeTab)
        }
        if (searchText) {
          params.append('search', searchText)
        }

        const token = localStorage.getItem('access_token')
        if (!token) {
          console.warn('No access token found')
          setFiltered([])
          setLoading(false)
          return
        }

        const response = await fetch(`/api/chat/history?${params}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          console.error('History API error:', response.status)
          setFiltered([])
          setLoading(false)
          return
        }

        const data = await response.json()

        // 适配新旧返回格式
        const historyItems = Array.isArray(data) ? data : (data.items || [])
        setFiltered(historyItems)

        // 更新分页信息
        if (!Array.isArray(data)) {
          setPaginationData({
            total: data.total || 0,
            total_pages: data.total_pages || 1
          })
        } else {
          setPaginationData({
            total: historyItems.length,
            total_pages: 1
          })
        }

        // 同步更新父组件的 items（用于 reinvoke 查找 actualIndex）
        if (activeTab === 'all' && currentPage === 1 && !searchText && setItems) {
          setItems(historyItems)
        }
      } catch (error) {
        console.error('Failed to fetch history:', error)
        setFiltered([])
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [activeTab, currentPage, searchText, setItems])

  // 获取各分类的记录数
  useEffect(() => {
    const fetchCounts = async () => {
      const token = localStorage.getItem('access_token')
      if (!token) return
      try {
        const resp = await fetch('/api/chat/history/counts?deduplicate=true', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (resp.ok) setCategoryCounts(await resp.json())
      } catch (_) { /* ignore */ }
    }
    fetchCounts()
  }, [activeTab, currentPage, searchText])

  // Tab切换时重置页码
  const handleTabChange = (tabId) => {
    setActiveTab(tabId)
    setCurrentPage(1)
  }

  // 搜索时重置页码
  const handleSearchChange = (text) => {
    setSearchText(text)
    setCurrentPage(1)
  }

  // 计算哪些记录可以被删除（用于样式控制）
  const selectableForDelete = useCallback((item) => {
    if (!currentUser) return false
    const userRole = currentUser.role || currentUser.user_role
    if (userRole === 'sys' || userRole === 'admin') return true
    return item.user_id === currentUser.id || item.user_id === currentUser.user_id
  }, [currentUser])

  useEffect(() => {
    if (!listRef.current || filtered.length === 0) return
    const first = listRef.current.querySelector('[data-history-item="0"]')
    if (first) first.scrollIntoView({ block: 'start' })
  }, [filtered.length, searchText])

  const toggle = useCallback((ts, e) => {
    e.stopPropagation()
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(ts) ? next.delete(ts) : next.add(ts)
      return next
    })
  }, [])

  const handleDelete = () => {
    if (selected.size === 0) return
    if (!items || items.length === 0) return

    // Map selected timestamps back to indices in the original items array
    const indices = items
      .map((item, i) => (selected.has(item.timestamp) ? i : -1))
      .filter((i) => i !== -1)
    removeEntries(indices)
    setSelected(new Set())
  }

  const handleReinvoke = (e, item, index) => {
    e.stopPropagation()
    if (onReinvoke) {
      onReinvoke(index)
    }
  }

  return (
    <aside className={s.panel}>
      <div className={s.header}>
        <h3>历史记录</h3>
        {selected.size > 0 && (
          <button className={s.deleteBtn} onClick={handleDelete}>
            删除历史
          </button>
        )}
      </div>

      {/* Pill分类按钮 */}
      <div className={s.pills}>
        {tabs.map(tab => {
          const count = categoryCounts[tab.id]
          return (
            <button
              key={tab.id}
              className={`${s.pill} ${activeTab === tab.id ? s.pillActive : ''}`}
              onClick={() => handleTabChange(tab.id)}
            >
              {tab.label}
              {count != null && <span className={s.pillCount}>{count}</span>}
            </button>
          )
        })}
      </div>

      <div className={s.searchWrap}>
        <input
          className={s.searchInput}
          type="text"
          placeholder="搜索历史记录..."
          value={searchText}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
      </div>

      <div className={s.list} ref={listRef}>
        {loading && <div className={s.empty}>加载中...</div>}
        {!loading && filtered.length === 0 && <div className={s.empty}>{searchText ? '无匹配记录' : '暂无历史记录'}</div>}
        {!loading && filtered.map((item, idx) => {
          // Find the actual index in the original items array (with safety check)
          const actualIndex = (items && items.length > 0)
            ? items.findIndex((i) => i.timestamp === item.timestamp)
            : -1
          const canDeleteThis = selectableForDelete(item)

          return (
            <div
              key={item.timestamp || idx}
              className={`${s.item} ${!canDeleteThis ? s.itemNoDelete : ''}`}
              data-history-item={idx === 0 ? '0' : undefined}
              onClick={() => onSelect && onSelect(item)}
            >
              <input
                type="checkbox"
                className={s.checkbox}
                checked={selected.has(item.timestamp)}
                onChange={(e) => toggle(item.timestamp, e)}
                disabled={!canDeleteThis}
              />
              <div className={s.itemContent}>
                <span className={s.itemText}>{item.query}</span>
              </div>
              <button
                className={s.reinvokeBtn}
                onClick={(e) => handleReinvoke(e, item, actualIndex)}
                title="重新运行"
              >
                ↻
              </button>
            </div>
          )
        })}
      </div>

      {/* 分页组件 */}
      <Pagination
        currentPage={currentPage}
        totalPages={paginationData.total_pages}
        onPageChange={setCurrentPage}
      />
    </aside>
  )
}
