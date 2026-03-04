import { useState } from 'react'
import s from './ProfileSection.module.css'
import { ChevronDown, ChevronRight } from 'lucide-react'

const NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三', '十四']

export default function ProfileSection({ title, defaultOpen = true, index = 0, children }) {
  const [open, setOpen] = useState(defaultOpen)
  const num = NUM[index] || ''

  return (
    <div className={s.section}>
      <div className={s.header} onClick={() => setOpen(!open)}>
        <span className={s.title}>{num}、{title}</span>
        {open ? <ChevronDown size={18} className={s.toggleIcon} /> : <ChevronRight size={18} className={s.toggleIcon} />}
      </div>
      {open && <div className={s.body}>{children}</div>}
    </div>
  )
}
