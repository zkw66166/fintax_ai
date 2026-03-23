import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { ArrowLeft, Printer, Download, Loader2 } from 'lucide-react'
import { generateReportStream, fetchReport } from '../../services/api'
import s from './ProfileReport.module.css'

function parseSSE(text) {
  const events = []
  const lines = text.split('\n')
  let currentEvent = null
  let currentData = ''

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim()
    } else if (line.startsWith('data: ')) {
      currentData = line.slice(6)
    } else if (line === '' && currentEvent) {
      try {
        events.push({ event: currentEvent, data: JSON.parse(currentData) })
      } catch { /* skip */ }
      currentEvent = null
      currentData = ''
    }
  }
  return events
}

export default function ProfileReport({ context, onBack }) {
  const [content, setContent] = useState('')
  const [status, setStatus] = useState('idle') // idle | generating | completed | failed
  const [stage, setStage] = useState('')
  const [error, setError] = useState(null)
  const abortRef = useRef(null)
  const contentRef = useRef('')
  const startedRef = useRef(false)

  const startGeneration = useCallback(async () => {
    if (!context?.taxpayerId) return
    setStatus('generating')
    setContent('')
    setError(null)
    contentRef.current = ''

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await generateReportStream(context.taxpayerId, context.year, controller.signal)
      if (!res.ok) {
        setError(`请求失败: ${res.status}`)
        setStatus('failed')
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          const events = parseSSE(part + '\n\n')
          for (const evt of events) {
            if (evt.event === 'stage') {
              setStage(evt.data.text || '')
            } else if (evt.event === 'meta') {
              // report_id received, could store if needed
            } else if (evt.event === 'chunk') {
              contentRef.current += evt.data.text || ''
              setContent(contentRef.current)
            } else if (evt.event === 'done') {
              if (evt.data.error && !evt.data.text) {
                setError(evt.data.error)
                setStatus('failed')
              } else {
                if (evt.data.text && evt.data.text.length > contentRef.current.length) {
                  setContent(evt.data.text)
                }
                setStatus('completed')
              }
            }
          }
        }
      }

      if (status !== 'failed') setStatus('completed')
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message)
        setStatus('failed')
      }
    }
  }, [context])

  const loadExistingReport = useCallback(async () => {
    if (!context?.reportId) return
    setStatus('generating')
    try {
      const data = await fetchReport(context.reportId)
      setContent(data.content || '')
      setStatus(data.status === 'completed' ? 'completed' : 'failed')
      if (data.error_msg) setError(data.error_msg)
    } catch (e) {
      setError(e.message)
      setStatus('failed')
    }
  }, [context])

  useEffect(() => {
    if (context?.mode === 'generate') {
      if (!startedRef.current) {
        startedRef.current = true
        startGeneration()
      }
    } else if (context?.mode === 'view') {
      loadExistingReport()
    }
    return () => { /* 不终止：后台继续生成 */ }
  }, [context, startGeneration, loadExistingReport])

  const handlePrint = () => window.print()
  const handleDownload = () => window.print() // browser "Save as PDF"

  return (
    <div className={s.reportPage}>
      <div className={`${s.toolbar} no-print`}>
        <button className={s.backBtn} onClick={onBack}>
          <ArrowLeft size={16} /> 返回
        </button>
        <div className={s.toolbarTitle}>
          {context?.taxpayerName || ''} — {context?.year}年度 企业经营与财税分析报告
        </div>
        <div className={s.toolbarActions}>
          {status === 'completed' && (
            <>
              <button className={s.actionBtn} onClick={handlePrint} title="打印">
                <Printer size={14} /> 打印
              </button>
              <button className={s.actionBtn} onClick={handleDownload} title="下载PDF">
                <Download size={14} /> 下载PDF
              </button>
            </>
          )}
        </div>
      </div>

      {status === 'generating' && (
        <div className={s.statusBar}>
          <Loader2 size={16} className={s.spin} />
          <span>{stage || '正在生成报告...'}</span>
        </div>
      )}

      {error && (
        <div className={s.errorBar}>{error}</div>
      )}

      <div className={s.scrollWrap}>
        <div className={s.disclaimer}>
          <div className={s.disclaimerTitle}>⚠ 报告声明与风险提示</div>
          本报告由惠盈智能AI基于企业画像数据自动生成，仅供内部参考与辅助决策使用，不构成正式审计意见、税务鉴证结论或法律建议。报告中的分析、判断及建议均基于所提供数据的完整性与准确性，可能存在因数据缺失、口径差异或模型局限导致的偏差。涉及税收优惠适用、税务筹划方案及合规风险评估等内容，应以主管税务机关的最终认定为准，建议结合注册会计师、注册税务师等专业人士意见审慎决策。使用本报告所产生的任何后果，由使用方自行承担。
        </div>
        <div className={s.reportContent}>
          {content ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : status === 'generating' ? (
            <div className={s.placeholder}>报告生成中，请稍候...</div>
          ) : status === 'idle' ? null : (
            <div className={s.placeholder}>暂无报告内容</div>
          )}
        </div>
      </div>
    </div>
  )
}
