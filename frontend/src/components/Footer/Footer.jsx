import s from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={s.footer}>
      <span>&copy; 2024 智能财税咨询系统. All rights reserved.</span>
      <span>版本 v1.0.0 | 帮助中心 | 技术支持</span>
    </footer>
  )
}
