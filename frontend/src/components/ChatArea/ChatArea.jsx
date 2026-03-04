import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react'
import useSSE from '../../hooks/useSSE'
import { saveHistoryEntry, deleteHistory, interpretStream, reinvokeFromHistory } from '../../services/api'
import { parseSSE } from '../../utils/sseParser'
import ChatMessage from '../ChatMessage/ChatMessage'
import ChatInput from '../ChatInput/ChatInput'
import s from './ChatArea.module.css'

const ChatArea = forwardRef(function ChatArea(
  { messages, setMessages, onQueryDone, responseMode, onResponseModeChange, thinkingMode, onThinkingModeChange, selectedCompanyId, pendingInputText, onPendingInputTextConsumed },
  ref,
) {
  const { isStreaming, startStream, cancel } = useSSE()
  const bottomRef = useRef(null)
  const containerRef = useRef(null)
  const atBottomRef = useRef(true)
  const forceScrollRef = useRef(false)
  const msgRefs = useRef([])
  const [showToBottom, setShowToBottom] = useState(false)

  // Conversation depth state (default: 3 turns, disabled by default)
  const [conversationDepth, setConversationDepth] = useState(3)
  const [conversationEnabled, setConversationEnabled] = useState(false)

  // Selection mode state
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [selectedIndices, setSelectedIndices] = useState(new Set())
  // Highlight state for scroll-to
  const [highlightIdx, setHighlightIdx] = useState(null)

  // Interpretation state: msgId -> { text, status: 'streaming'|'done'|'error' }
  const [interpretations, setInterpretations] = useState({})
  const interpretControllersRef = useRef({})

  // Ref to always hold latest thinkingMode (avoids stale closure in handleSend)
  const thinkingModeRef = useRef(thinkingMode)
  useEffect(() => { thinkingModeRef.current = thinkingMode }, [thinkingMode])

  // Expose scrollToMessage and handleReinvoke to parent via ref
  useImperativeHandle(ref, () => ({
    scrollToMessage(index) {
      const el = msgRefs.current[index]
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        setHighlightIdx(index)
        setTimeout(() => setHighlightIdx(null), 2000)
      }
    },
    handleReinvoke(historyIndex, overrideThinkingMode) {
      handleReinvokeInternal(historyIndex, overrideThinkingMode)
    },
  }))

  // Keep msgRefs in sync with messages length
  useEffect(() => {
    msgRefs.current = msgRefs.current.slice(0, messages.length)
  }, [messages.length])

  const getQuestionForIndex = useCallback((index) => {
    if (index == null || index < 0) return ''
    for (let i = index; i >= 0; i -= 1) {
      const msg = messages[i]
      if (msg?.role === 'user') return msg.content || ''
    }
    return ''
  }, [messages])

  const triggerInterpretation = useCallback(async (msgId, query, result, options) => {
    const controller = new AbortController()
    interpretControllersRef.current[msgId] = controller
    setInterpretations((prev) => ({ ...prev, [msgId]: { text: '', status: 'streaming' } }))

    // Trim payload: strip chart_data, timings, cap results at 50 rows
    const trimmed = {
      success: result.success,
      route: result.route,
      results: (result.results || []).slice(0, 50),
      intent: result.intent,
      entities: result.entities,
      metric_results: result.metric_results,
      cross_domain_summary: result.cross_domain_summary,
      sub_results: result.sub_results,
    }
    if (result.display_data) {
      const { chart_data, ...rest } = result.display_data
      trimmed.display_data = rest
    }

    try {
      const response = await interpretStream(query, trimmed, controller.signal, { ...options })
      if (!response.ok) {
        setInterpretations((prev) => ({ ...prev, [msgId]: { text: '', status: 'error' } }))
        return
      }
      for await (const evt of parseSSE(response)) {
        if (controller.signal.aborted) break
        if (evt.event === 'chunk') {
          setInterpretations((prev) => ({
            ...prev,
            [msgId]: { text: (prev[msgId]?.text || '') + (evt.data?.text || ''), status: 'streaming' },
          }))
        } else if (evt.event === 'done') {
          setInterpretations((prev) => ({
            ...prev,
            [msgId]: { text: evt.data?.text || prev[msgId]?.text || '', status: 'done' },
          }))
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setInterpretations((prev) => ({ ...prev, [msgId]: { text: '', status: 'error' } }))
      }
    } finally {
      delete interpretControllersRef.current[msgId]
    }
  }, [])

  // Smart scroll: only auto-scroll when user is at bottom
  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    atBottomRef.current = atBottom
    setShowToBottom(!atBottom)
  }

  const scrollToBottom = (behavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior, block: 'end' })
  }

  // Build conversation history for multi-turn context
  const buildConversationHistory = useCallback(() => {
    if (!conversationEnabled || messages.length === 0) {
      return null
    }

    // Extract last N turns (N*2 messages: user + assistant pairs)
    const turnCount = conversationDepth
    const messageCount = turnCount * 2

    // Filter out messages that are still loading or have errors
    const validMessages = messages.filter(msg =>
      msg.role === 'user' || (msg.role === 'assistant' && msg.status === 'done')
    )

    // Take the most recent messages
    const recentMessages = validMessages.slice(-messageCount)

    // Need at least one complete turn (2 messages) to provide context
    if (recentMessages.length < 2) {
      return null
    }

    // Format as OpenAI-compatible messages with metadata
    return recentMessages.map(msg => {
      const formatted = {
        role: msg.role,
        content: msg.content || '',
        timestamp: new Date().toISOString(),
      }

      // Add metadata for assistant messages (contains entities for context inheritance)
      if (msg.role === 'assistant' && msg.result) {
        formatted.metadata = {
          route: msg.route || 'financial_data',
          domain: msg.result.intent?.domain || 'vat',
          entities: msg.result.entities || {},
        }
      }

      return formatted
    })
  }, [messages, conversationDepth, conversationEnabled])

  // Clear conversation context
  const handleClearContext = useCallback(() => {
    // Just disable conversation temporarily or clear messages
    // For now, we'll just show a visual indicator that context was cleared
    console.log('Conversation context cleared')
  }, [])

  useEffect(() => {
    if (forceScrollRef.current) {
      scrollToBottom()
      forceScrollRef.current = false
      setShowToBottom(false)
      return
    }
    if (atBottomRef.current) {
      scrollToBottom()
      setShowToBottom(false)
    }
  }, [messages])

  const handleSend = useCallback(
    (query) => {
      const currentThinkingMode = thinkingModeRef.current
      const ts = new Date().toLocaleTimeString()
      const userMsg = { id: `u-${Date.now()}`, role: 'user', content: query, ts }
      const aiId = `a-${Date.now()}`
      const aiMsg = { id: aiId, role: 'assistant', status: 'loading', chunks: [], route: null, result: null, content: '', pipelineDetail: null, responseMode, cacheHit: false }

      // Build conversation history before adding new messages
      const conversationHistory = buildConversationHistory()

      forceScrollRef.current = true
      atBottomRef.current = true
      setMessages((prev) => [...prev, userMsg, aiMsg])

      const update = (fn) =>
        setMessages((prev) => prev.map((m) => (m.id === aiId ? fn(m) : m)))

      startStream(query, (evt) => {
        if (evt.event === 'stage') {
          update((m) => ({ ...m, route: evt.data.route, status: 'loading', stageText: evt.data.text || '' }))
        } else if (evt.event === 'chunk') {
          update((m) => ({ ...m, status: 'streaming', chunks: [...m.chunks, evt.data.text] }))
        } else if (evt.event === 'done') {
          const result = evt.data
          const isCacheHit = !!result.cache_hit
          const cacheKey = result.cache_key || ''
          let content = ''
          if (result.clarification) {
            content = `⚠️ 需要澄清\n\n${result.clarification}`
          } else if (result.route === 'tax_incentive' || result.route === 'regulation') {
            content = result.answer || ''
          } else if (result.success && result.results) {
            // Check for empty data message
            if (result.results.length === 0 && result.empty_data_message) {
              content = `💡 ${result.empty_data_message}`
            } else {
              content = ''
            }
          } else if (!result.success) {
            content = `❌ 查询失败\n\n${result.error || '未知错误'}`
          }

          const entities = result.entities ? JSON.stringify(result.entities, null, 2) : '无'
          const intent = result.intent ? JSON.stringify(result.intent, null, 2) : '无'
          let sql = result.sql || ''
          if (!sql && result.sub_results) {
            sql = result.sub_results
              .filter((sr) => sr.sql)
              .map((sr) => `-- [${sr.domain || '?'}]\n${sr.sql}`)
              .join('\n\n')
          }

          update((m) => ({
            ...m,
            status: 'done',
            result,
            route: result.route || m.route || 'financial_data',
            content: m.chunks.length > 0 ? m.chunks.join('') : content,
            responseMode: result.response_mode || responseMode,
            pipelineDetail: { entities, intent, sql: sql || '无' },
            cacheHit: isCacheHit,
          }))

          forceScrollRef.current = true

          // Handle interpretation based on cache hit status
          const rMode = result.response_mode || responseMode
          const isFinancialResult =
            result.route !== 'tax_incentive' &&
            result.route !== 'regulation' &&
            result.success &&
            (result.results?.length > 0 || result.metric_results?.length > 0) &&
            rMode !== 'concise'

          if (isCacheHit && !result.need_reinterpret && result.cached_interpretation) {
            // Quick mode with cached interpretation: show directly
            if (isFinancialResult) {
              setInterpretations((prev) => ({
                ...prev,
                [aiId]: { text: result.cached_interpretation, status: 'done' },
              }))
            }
          } else if (isFinancialResult) {
            // Think / deep / no cached interpretation: trigger LLM interpretation
            // For "think" mode re-interpretation, always use "detailed" for full analysis
            const interpretMode = (result.need_reinterpret) ? 'detailed' : rMode
            triggerInterpretation(aiId, query, result, { responseMode: interpretMode, companyId: selectedCompanyId, cacheKey })
          }

          const entry = {
            query,
            status: result.success ? 'success' : 'error',
            main_output: content,
            entity_text: entities,
            intent_text: intent,
            sql_text: sql || '无',
            route: result.route,
            result_count: result.result_count,
            timestamp: ts,
            cache_key: cacheKey,
            // NEW: Enhanced fields for re-invocation
            conversation_history: conversationHistory || [],
            conversation_enabled: !!conversationHistory && conversationHistory.length > 0,
            conversation_depth: conversationDepth,
            response_mode: responseMode,
            thinking_mode: currentThinkingMode,
            result: result,  // Full pipeline result including display_data
            company_id: selectedCompanyId,
          }
          onQueryDone(entry)
          saveHistoryEntry(entry).catch(() => {})
        } else if (evt.event === 'error') {
          update((m) => ({ ...m, status: 'error', content: evt.data.message || '请求失败' }))
          forceScrollRef.current = true
        }
      }, {
        responseMode,
        companyId: selectedCompanyId,
        thinkingMode: currentThinkingMode,
        conversationHistory,
        conversationDepth,
      })
    },
    [startStream, setMessages, onQueryDone, responseMode, selectedCompanyId, triggerInterpretation, setInterpretations, buildConversationHistory, conversationDepth],
  )

  const handleReinvokeInternal = useCallback(
    async (historyIndex, overrideThinkingMode) => {
      const effectiveThinkingMode = overrideThinkingMode || thinkingModeRef.current
      const ts = new Date().toLocaleTimeString()
      const aiId = `a-${Date.now()}`
      const aiMsg = { id: aiId, role: 'assistant', status: 'loading', chunks: [], route: null, result: null, content: '', pipelineDetail: null, responseMode, cacheHit: false }

      forceScrollRef.current = true
      atBottomRef.current = true
      setMessages((prev) => [...prev, aiMsg])

      const update = (fn) =>
        setMessages((prev) => prev.map((m) => (m.id === aiId ? fn(m) : m)))

      try {
        const controller = new AbortController()
        const response = await reinvokeFromHistory(historyIndex, effectiveThinkingMode, controller.signal)

        if (!response.ok) {
          update((m) => ({ ...m, status: 'error', content: '重新运行失败' }))
          return
        }

        for await (const evt of parseSSE(response)) {
          if (evt.event === 'stage') {
            update((m) => ({ ...m, route: evt.data.route, status: 'loading', stageText: evt.data.text || '' }))
          } else if (evt.event === 'chunk') {
            update((m) => ({ ...m, status: 'streaming', chunks: [...m.chunks, evt.data.text] }))
          } else if (evt.event === 'done') {
            const result = evt.data
            const isCacheHit = !!result.cache_hit
            const cacheKey = result.cache_key || ''
            let content = ''
            if (result.clarification) {
              content = `⚠️ 需要澄清\n\n${result.clarification}`
            } else if (result.route === 'tax_incentive' || result.route === 'regulation') {
              content = result.answer || ''
            } else if (result.success && result.results) {
              if (result.results.length === 0 && result.empty_data_message) {
                content = `💡 ${result.empty_data_message}`
              } else {
                content = ''
              }
            } else if (!result.success) {
              content = `❌ 查询失败\n\n${result.error || '未知错误'}`
            }

            const entities = result.entities ? JSON.stringify(result.entities, null, 2) : '无'
            const intent = result.intent ? JSON.stringify(result.intent, null, 2) : '无'
            let sql = result.sql || ''
            if (!sql && result.sub_results) {
              sql = result.sub_results
                .filter((sr) => sr.sql)
                .map((sr) => `-- [${sr.domain || '?'}]\n${sr.sql}`)
                .join('\n\n')
            }

            update((m) => ({
              ...m,
              status: 'done',
              result,
              route: result.route || m.route || 'financial_data',
              content: m.chunks.length > 0 ? m.chunks.join('') : content,
              responseMode: result.response_mode || responseMode,
              pipelineDetail: { entities, intent, sql: sql || '无' },
              cacheHit: isCacheHit,
            }))

            forceScrollRef.current = true

            // Handle interpretation
            const rMode = result.response_mode || responseMode
            const isFinancialResult =
              result.route !== 'tax_incentive' &&
              result.route !== 'regulation' &&
              result.success &&
              (result.results?.length > 0 || result.metric_results?.length > 0) &&
              rMode !== 'concise'

            if (isCacheHit && !result.need_reinterpret && result.cached_interpretation) {
              if (isFinancialResult) {
                setInterpretations((prev) => ({
                  ...prev,
                  [aiId]: { text: result.cached_interpretation, status: 'done' },
                }))
              }
            } else if (isFinancialResult) {
              const interpretMode = (result.need_reinterpret) ? 'detailed' : rMode
              // Extract query from result or use a placeholder
              const query = result.entities?.query || '历史查询'
              triggerInterpretation(aiId, query, result, { responseMode: interpretMode, companyId: selectedCompanyId, cacheKey })
            }
          } else if (evt.event === 'error') {
            update((m) => ({ ...m, status: 'error', content: evt.data.message || '请求失败' }))
            forceScrollRef.current = true
          }
        }
      } catch (err) {
        update((m) => ({ ...m, status: 'error', content: '重新运行失败' }))
      }
    },
    [setMessages, responseMode, selectedCompanyId, triggerInterpretation, setInterpretations],
  )

  const handleClear = () => {
    if (messages.length === 0) return
    if (!window.confirm('确定要清空所有对话记录吗？')) return
    cancel()
    Object.values(interpretControllersRef.current).forEach((c) => c.abort())
    interpretControllersRef.current = {}
    setInterpretations({})
    setMessages([])
    setIsSelectionMode(false)
    setSelectedIndices(new Set())
    deleteHistory([]).catch(() => {})
  }

  const handleExport = () => {
    if (messages.length === 0) return
    const container = containerRef.current
    if (!container) return
    const clone = container.cloneNode(true)

    // Replace canvas elements with static images
    const origCanvases = container.querySelectorAll('canvas')
    const cloneCanvases = clone.querySelectorAll('canvas')
    cloneCanvases.forEach((cvs, i) => {
      try {
        const img = document.createElement('img')
        img.src = origCanvases[i].toDataURL('image/png')
        img.style.maxWidth = '100%'
        cvs.parentNode.replaceChild(img, cvs)
      } catch (_) { /* cross-origin canvas, skip */ }
    })

    // Remove interactive elements
    clone.querySelectorAll('button, input[type="checkbox"]').forEach((el) => el.remove())
    // Remove pipeline detail collapsible sections
    clone.querySelectorAll('details').forEach((el) => el.remove())

    const win = window.open('', '_blank')
    if (!win) return
    win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"/><title>对话导出</title><style>
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;padding:20px;max-width:900px;margin:0 auto}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px 10px;font-size:13px}
img{max-width:100%;height:auto}
@page{size:A4;margin:15mm}
@media print{
  body{padding:0;overflow:visible}
  *{overflow:visible !important}
  tr,li{page-break-inside:avoid}
  h2,h3,h4{page-break-after:avoid}
  table{page-break-inside:auto}
  img{page-break-inside:avoid;max-height:90vh}
}
</style></head><body><h2>智能财税咨询 - 对话记录</h2>${clone.innerHTML}</body></html>`)
    win.document.close()
    setTimeout(() => win.print(), 500)
  }

  const handleToggleSelect = (index) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev)
      next.has(index) ? next.delete(index) : next.add(index)
      return next
    })
  }

  const handleDeleteSelected = async () => {
    if (selectedIndices.size === 0) return

    // Map selected message indices to history indices by matching query text
    // This is a best-effort approach since messages and history may not be perfectly aligned
    const selectedMessages = messages.filter((_, i) => selectedIndices.has(i))
    const userQueries = selectedMessages
      .filter((m) => m.role === 'user')
      .map((m) => m.content)

    // Find matching history indices (this assumes history items are loaded in App.jsx)
    // Since we don't have direct access to history items here, we'll just delete locally
    // and rely on the user to delete from history panel if needed
    // TODO: Consider passing history items as prop for better sync

    setMessages((prev) => prev.filter((_, i) => !selectedIndices.has(i)))
    setSelectedIndices(new Set())
    setIsSelectionMode(false)

    // Note: For now, message deletion is local-only
    // Users should use history panel deletion for persistent removal
  }

  return (
    <div className={s.wrap}>
      <div className={s.titleBar}>
        <div className={s.titleLeft}>
          <h2>AI智能问答</h2>
          <p>基于专业税务财务知识库的智能问答</p>
        </div>
        <div className={s.titleActions}>
          <button onClick={() => setIsSelectionMode(true)}>消息管理</button>
          <button onClick={handleClear}>清空对话</button>
          <button onClick={handleExport}>导出PDF</button>
        </div>
      </div>

      <div className={s.messages} ref={containerRef} onScroll={handleScroll}>
        {messages.map((msg, i) => (
          <div
            key={msg.id}
            ref={(el) => { msgRefs.current[i] = el }}
            className={highlightIdx === i ? s.highlight : undefined}
          >
            <ChatMessage
              msg={msg}
              interpretation={interpretations[msg.id]}
              isSelectionMode={isSelectionMode}
              isSelected={selectedIndices.has(i)}
              onToggleSelect={() => handleToggleSelect(i)}
              questionText={msg.role === 'assistant' ? getQuestionForIndex(i - 1) : ''}
            />
          </div>
        ))}
        <div ref={bottomRef} />
        {showToBottom && (
          <button className={s.toBottomBtn} onClick={() => scrollToBottom()} aria-label="回到底部" title="回到底部">
            ↓
          </button>
        )}
      </div>

      {isSelectionMode ? (
        <div className={s.selectionBar}>
          <span>已选择 {selectedIndices.size} 条消息</span>
          <div>
            <button className={s.selCancelBtn} onClick={() => { setIsSelectionMode(false); setSelectedIndices(new Set()) }}>取消</button>
            <button className={s.selDeleteBtn} onClick={handleDeleteSelected} disabled={selectedIndices.size === 0}>删除</button>
          </div>
        </div>
      ) : (
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          onCancel={cancel}
          responseMode={responseMode}
          onModeChange={onResponseModeChange}
          thinkingMode={thinkingMode}
          onThinkingModeChange={onThinkingModeChange}
          pendingInputText={pendingInputText}
          onPendingInputTextConsumed={onPendingInputTextConsumed}
          conversationDepth={conversationDepth}
          onConversationDepthChange={setConversationDepth}
          conversationEnabled={conversationEnabled}
          onConversationEnabledChange={setConversationEnabled}
          onClearContext={handleClearContext}
        />
      )}
    </div>
  )
})

export default ChatArea
