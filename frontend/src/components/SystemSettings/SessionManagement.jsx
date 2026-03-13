import { useState, useEffect, useCallback, useMemo } from 'react'
import s from './SessionManagement.module.css'
import { fetchDeletedHistory, restoreHistory, permanentDeleteHistory } from '../../services/api'
import { RotateCcw, Trash2 } from 'lucide-react'

const ROUTE_LABELS = {
  financial_data: '财税数据',
  tax_incentive: '税收优惠',
  regulation: '法规知识',
  mixed_analysis: '综合分析',
}

const ROUTE_BADGE = {
  financial_data: 'badgeFinancial',
  tax_incentive: 'badgeTax',
  regulation: 'badgeRegulation',
  mixed_analysis: 'badgeMixed',
}

const COLUMNS = [
  { key: 'query', label: '查询内容' },
  { key: 'route', label: '分类' },
  { key: 'creator_name', label: '创建者' },
  { key: 'deleter_name', label: '删除者' },
  { key: 'timestamp', label: '首次创建' },
  { key: 'deleted_at', label: '删除时间' },
]

function formatTime(ts) {
  if (!ts) return '-'
  try {
    const d = new Date(ts)
    if (isNaN(d.getTime())) return ts
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}

export default function SessionManagement() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [sortKey, setSortKey] = useState('deleted_at')
  const [sortAsc, setSortAsc] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchDeletedHistory()
      setItems(data.items || [])
    } catch { setItems([]) }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const sorted = useMemo(() => {
    const copy = [...items]
    copy.sort((a, b) => {
      const va = a[sortKey] ?? ''
      const vb = b[sortKey] ?? ''
      const cmp = String(va).localeCompare(String(vb), 'zh-CN')
      return sortAsc ? cmp : -cmp
    })
    return copy
  }, [items, sortKey, sortAsc])

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(true) }
  }

  const toggleSelect = (ts) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(ts) ? next.delete(ts) : next.add(ts)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === sorted.length) setSelected(new Set())
    else setSelected(new Set(sorted.map(i => i.timestamp)))
  }

  const handleRestore = async (timestamps) => {
    await restoreHistory(timestamps)
    setSelected(new Set())
    load()
  }

  const handleRestoreAll = async () => {
    await restoreHistory([], true)
    setSelected(new Set())
    load()
  }

  const handlePermanentDelete = async (timestamps) => {
    await permanentDeleteHistory(timestamps)
    setSelected(new Set())
    setConfirmAction(null)
    load()
  }

  const selectedTimestamps = Array.from(selected)

  return (
    <div className={s.wrap}>
      <div className={s.header}>
        <div className={s.title}>
          已删除的历史记录
          <span className={s.titleCount}>({items.length}条)</span>
        </div>
        <div className={s.toolbar}>
          <button
            className={`${s.btn} ${s.btnPrimary}`}
            disabled={selected.size === 0}
            onClick={() => handleRestore(selectedTimestamps)}
          >
            <RotateCcw size={14} /> 恢复选中
          </button>
          <button
            className={s.btn}
            disabled={items.length === 0}
            onClick={handleRestoreAll}
          >
            恢复全部
          </button>
          <button
            className={`${s.btn} ${s.btnDanger}`}
            disabled={selected.size === 0}
            onClick={() => setConfirmAction('delete')}
          >
            <Trash2 size={14} /> 彻底删除
          </button>
        </div>
      </div>

      {loading ? (
        <div className={s.empty}>加载中...</div>
      ) : sorted.length === 0 ? (
        <div className={s.empty}>暂无已删除的历史记录</div>
      ) : (
        <table className={s.table}>
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <input
                  type="checkbox"
                  className={s.checkbox}
                  checked={selected.size === sorted.length && sorted.length > 0}
                  onChange={toggleAll}
                />
              </th>
              {COLUMNS.map(col => (
                <th key={col.key} onClick={() => toggleSort(col.key)}>
                  {col.label}
                  <span className={`${s.sortIcon} ${sortKey === col.key ? s.sortActive : ''}`}>
                    {sortKey === col.key ? (sortAsc ? '▲' : '▼') : '↕'}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(item => (
              <tr key={item.timestamp}>
                <td>
                  <input
                    type="checkbox"
                    className={s.checkbox}
                    checked={selected.has(item.timestamp)}
                    onChange={() => toggleSelect(item.timestamp)}
                  />
                </td>
                <td className={s.queryCell} title={item.query}>{item.query}</td>
                <td>
                  <span className={`${s.badge} ${s[ROUTE_BADGE[item.route]] || ''}`}>
                    {ROUTE_LABELS[item.route] || item.route || '未分类'}
                  </span>
                </td>
                <td>{item.creator_name}</td>
                <td>{item.deleter_name}</td>
                <td>{formatTime(item.timestamp)}</td>
                <td>{formatTime(item.deleted_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {confirmAction === 'delete' && (
        <div className={s.overlay} onClick={() => setConfirmAction(null)}>
          <div className={s.confirmBox} onClick={e => e.stopPropagation()}>
            <div className={s.confirmTitle}>确认彻底删除</div>
            <div className={s.confirmText}>
              即将彻底删除 {selected.size} 条记录及其关联的缓存文件。
              此操作不可恢复，请确认。
            </div>
            <div className={s.confirmActions}>
              <button className={s.btn} onClick={() => setConfirmAction(null)}>取消</button>
              <button
                className={`${s.btn} ${s.btnDanger}`}
                onClick={() => handlePermanentDelete(selectedTimestamps)}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
