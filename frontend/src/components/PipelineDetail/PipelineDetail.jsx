import { useState } from 'react'
import s from './PipelineDetail.module.css'

export default function PipelineDetail({ detail }) {
  const [open, setOpen] = useState(false)
  if (!detail) return null

  return (
    <div className={s.wrap}>
      <button className={s.toggle} onClick={() => setOpen(!open)}>
        <span className={`${s.arrow} ${open ? s.arrowOpen : ''}`}>▶</span>
        🔍 管线详情
      </button>
      {open && (
        <div className={s.body}>
          {detail.entities && detail.entities !== '无' && (
            <div className={s.section}>
              <h4>实体识别</h4>
              <pre className={s.pre}>{detail.entities}</pre>
            </div>
          )}
          {detail.intent && detail.intent !== '无' && (
            <div className={s.section}>
              <h4>意图解析 (Stage 1)</h4>
              <pre className={s.pre}>{detail.intent}</pre>
            </div>
          )}
          {detail.sql && detail.sql !== '无' && (
            <div className={s.section}>
              <h4>生成 SQL (Stage 2)</h4>
              <pre className={s.pre}>{detail.sql}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
