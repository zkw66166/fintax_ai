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
    (indices) => {
      deleteHistory(indices).catch(() => {})
      setItems((prev) => prev.filter((_, i) => !indices.includes(i)))
    },
    [setItems],
  )

  return { addEntry, removeEntries }
}
