import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react'
import useSSE from '../../hooks/useSSE'
import { saveHistoryEntry, deleteHistory } from '../../services/api'
import ChatMessage from '../ChatMessage/ChatMessage'
import ChatInput from '../ChatInput/ChatInput'
import s from './ChatArea.module.css'

const ChatArea = forwardRef(function ChatArea(
  { messages, setMessages, onQueryDone, responseMode, onResponseModeChange, selectedCompanyId, pendingInputText, onPendingInputTextConsumed },
  ref,
) {
  const { isStreaming, startStream, cancel } = useSSE()
  const bottomRef = useRef(null)
  const containerRef = useRef(null)
  const atBottomRef = useRef(true)
  const msgRefs = useRef([])

  // Selection mode state
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [selectedIndices, setSelectedIndices] = useState(new Set())
  // Highlight state for scroll-to
  const [highlightIdx, setHighlightIdx] = useState(null)

  // Expose scrollToMessage to parent via ref
  useImperativeHandle(ref, () => ({
    scrollToMessage(index) {
      const el = msgRefs.current[index]
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        setHighlightIdx(index)
        setTimeout(() => setHighlightIdx(null), 2000)
      }
    },
  }))

  // Keep msgRefs in sync with messages length
  useEffect(() => {
    msgRefs.current = msgRefs.current.slice(0, messages.length)
  }, [messages.length])

  // Smart scroll: only auto-scroll when user is at bottom
  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50
  }

  useEffect(() => {
    if (atBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSend = useCallback(
    (query) => {
      const ts = new Date().toLocaleTimeString()
      const userMsg = { id: `u-${Date.now()}`, role: 'user', content: query, ts }
      const aiId = `a-${Date.now()}`
      const aiMsg = { id: aiId, role: 'assistant', status: 'loading', chunks: [], route: null, result: null, content: '', pipelineDetail: null, responseMode }

      setMessages((prev) => [...prev, userMsg, aiMsg])

      const update = (fn) =>
        setMessages((prev) => prev.map((m) => (m.id === aiId ? fn(m) : m)))

      startStream(query, (evt) => {
        if (evt.event === 'stage') {
          update((m) => ({ ...m, route: evt.data.route, status: 'loading' }))
        } else if (evt.event === 'chunk') {
          update((m) => ({ ...m, status: 'streaming', chunks: [...m.chunks, evt.data.text] }))
        } else if (evt.event === 'done') {
          const result = evt.data
          let content = ''
          if (result.clarification) {
            content = `⚠️ 需要澄清\n\n${result.clarification}`
          } else if (result.route === 'tax_incentive' || result.route === 'regulation') {
            content = result.answer || ''
          } else if (result.success && result.results) {
            content = ''
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
          }))

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
          }
          onQueryDone(entry)
          saveHistoryEntry(entry).catch(() => {})
        } else if (evt.event === 'error') {
          update((m) => ({ ...m, status: 'error', content: evt.data.message || '请求失败' }))
        }
      }, { responseMode, companyId: selectedCompanyId })
    },
    [startStream, setMessages, onQueryDone, responseMode, selectedCompanyId],
  )

  const handleClear = () => {
    if (messages.length === 0) return
    if (!window.confirm('确定要清空所有对话记录吗？')) return
    cancel()
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
@media print{body{padding:0}div{page-break-inside:avoid}}
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

  const handleDeleteSelected = () => {
    if (selectedIndices.size === 0) return
    setMessages((prev) => prev.filter((_, i) => !selectedIndices.has(i)))
    setSelectedIndices(new Set())
    setIsSelectionMode(false)
  }

  return (
    <div className={s.wrap}>
      <div className={s.titleBar}>
        <div className={s.titleLeft}>
          <h2>AI智能问答</h2>
          <p>基于专业税务财务知识库的智能问答</p>
        </div>
        <div className={s.titleActions}>
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
              isSelectionMode={isSelectionMode}
              isSelected={selectedIndices.has(i)}
              onToggleSelect={() => handleToggleSelect(i)}
            />
          </div>
        ))}
        <div ref={bottomRef} />
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
          onToggleSelectionMode={() => setIsSelectionMode(true)}
          pendingInputText={pendingInputText}
          onPendingInputTextConsumed={onPendingInputTextConsumed}
        />
      )}
    </div>
  )
})

export default ChatArea
