import { useState, useCallback, useEffect, useRef } from 'react'
import useChatHistory from '../../hooks/useChatHistory'
import s from './HistoryPanel.module.css'

export default function HistoryPanel({ items, setItems, onSelect, onReinvoke }) {
  const [selected, setSelected] = useState(new Set())
  const [searchText, setSearchText] = useState('')
  const { removeEntries } = useChatHistory(items, setItems)
  const listRef = useRef(null)

  const filtered = searchText
    ? items.filter((item) => item.query.includes(searchText))
    : items

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
      <div className={s.searchWrap}>
        <input
          className={s.searchInput}
          type="text"
          placeholder="搜索历史记录..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
      </div>
      <div className={s.list} ref={listRef}>
        {filtered.length === 0 && <div className={s.empty}>{searchText ? '无匹配记录' : '暂无历史记录'}</div>}
        {filtered.map((item, idx) => {
          // Find the actual index in the original items array
          const actualIndex = items.findIndex((i) => i.timestamp === item.timestamp)
          return (
            <div
              key={item.timestamp}
              className={s.item}
              data-history-item={idx === 0 ? '0' : undefined}
              onClick={() => onSelect(item)}
            >
              <input
                type="checkbox"
                className={s.checkbox}
                checked={selected.has(item.timestamp)}
                onChange={(e) => toggle(item.timestamp, e)}
              />
              <span className={s.itemText}>{item.query}</span>
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
    </aside>
  )
}
