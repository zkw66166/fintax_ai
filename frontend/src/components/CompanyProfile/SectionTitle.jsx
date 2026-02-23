import s from './SectionTitle.module.css'

export default function SectionTitle({ name }) {
  return (
    <div className={s.wrap}>
      <span className={s.text}>{name}</span>
    </div>
  )
}
