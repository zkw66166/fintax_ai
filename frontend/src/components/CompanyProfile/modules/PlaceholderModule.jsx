import s from './PlaceholderModule.module.css'

export default function PlaceholderModule() {
  return (
    <div className={s.placeholder}>
      <span className={s.icon}>📋</span>
      <span className={s.text}>暂无数据，后续版本开放</span>
    </div>
  )
}
