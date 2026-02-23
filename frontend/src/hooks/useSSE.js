import { useState, useRef, useCallback } from 'react'
import { chatStream } from '../services/api'
import { parseSSE } from '../utils/sseParser'

export default function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false)
  const controllerRef = useRef(null)

  const startStream = useCallback(async (query, onEvent, options = {}) => {
    const controller = new AbortController()
    controllerRef.current = controller
    setIsStreaming(true)

    try {
      const response = await chatStream(query, controller.signal, options)
      if (!response.ok) {
        onEvent({ event: 'error', data: { message: `HTTP ${response.status}` } })
        return
      }
      for await (const evt of parseSSE(response)) {
        if (controller.signal.aborted) break
        onEvent(evt)
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        onEvent({ event: 'error', data: { message: err.message } })
      }
    } finally {
      setIsStreaming(false)
      controllerRef.current = null
    }
  }, [])

  const cancel = useCallback(() => {
    controllerRef.current?.abort()
  }, [])

  return { isStreaming, startStream, cancel }
}
