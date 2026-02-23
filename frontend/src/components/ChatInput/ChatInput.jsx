import { useState, useRef, useEffect } from 'react'
import s from './ChatInput.module.css'

const MODES = [
  { key: 'detailed', label: '图文' },
  { key: 'standard', label: '纯数据' },
  { key: 'concise', label: '简报' },
]

export default function ChatInput({ onSend, isStreaming, onCancel, responseMode, onModeChange, onToggleSelectionMode, pendingInputText, onPendingInputTextConsumed }) {
  const [text, setText] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    if (pendingInputText) {
      setText(pendingInputText)
      onPendingInputTextConsumed()
      ref.current?.focus()
    }
  }, [pendingInputText, onPendingInputTextConsumed])

  const handleSubmit = () => {
    const q = text.trim()
    if (!q || isStreaming) return
    onSend(q)
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === 'Escape' && isStreaming) {
      onCancel()
    }
  }

  return (
    <div className={s.wrap}>
      <div className={s.disclaimer}>
        AI 智能问答基于专业税务财务知识库，回答仅供参考，具体以相关法律法规为准
      </div>
      <div className={s.inputRow}>
        <textarea
          ref={ref}
          className={s.textarea}
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 500))}
          onKeyDown={handleKeyDown}
          placeholder="例如：2022-2025收入、利润变动情况；或小微企业优惠政策有哪些；或小微企业优惠需要申请吗"
          rows={2}
          maxLength={500}
        />
        {isStreaming ? (
          <button className={s.cancelBtn} onClick={onCancel}>取消</button>
        ) : (
          <button className={s.submitBtn} onClick={handleSubmit} disabled={!text.trim()}>
            提交咨询
          </button>
        )}
      </div>
      <div className={s.bottomRow}>
        <div className={s.modes}>
          {MODES.map((m) => (
            <span
              key={m.key}
              className={`${s.modeTag} ${responseMode === m.key ? s.active : ''}`}
              onClick={() => onModeChange(m.key)}
            >
              {m.label}
            </span>
          ))}
        </div>
        <div className={s.bottomRight}>
          <button className={s.manageBtn} onClick={onToggleSelectionMode}>管理消息</button>
          <span className={s.charCount}>{text.length}/500字符</span>
        </div>
      </div>
    </div>
  )
}
