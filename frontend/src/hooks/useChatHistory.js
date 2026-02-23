import { useEffect, useCallback } from 'react'
import { fetchHistory, saveHistoryEntry, deleteHistory } from '../services/api'

export default function useChatHistory(items, setItems) {
  useEffect(() => {
    fetchHistory()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) setItems(data)
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
