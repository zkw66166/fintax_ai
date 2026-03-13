import { useEffect, useCallback } from 'react'
import { fetchHistory, saveHistoryEntry, deleteHistory } from '../services/api'

export default function useChatHistory(items, setItems) {
  useEffect(() => {
    fetchHistory()
      .then((data) => {
        // 适配新的返回格式：{items: [], total: ...} 或旧格式：[]
        const historyItems = Array.isArray(data) ? data : (data.items || [])
        if (historyItems.length > 0) setItems(historyItems)
      })
      .catch(() => {})
  }, [setItems])

  const addEntry = useCallback(
    (entry) => {
      setItems((prev) => [entry, ...prev])
      saveHistoryEntry(entry).catch(() => {})
    },
    [setItems],
  )

  const removeEntries = useCallback(
    async (timestamps) => {
      try {
        const res = await deleteHistory(timestamps)
        const data = await res.json()
        if (data.ok && data.marked > 0) {
          setItems((prev) => prev.filter((item) => !timestamps.includes(item.timestamp)))
        }
      } catch { /* ignore */ }
    },
    [setItems],
  )

  return { addEntry, removeEntries }
}
