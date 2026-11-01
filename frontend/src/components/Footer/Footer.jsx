import s from './Footer.module.css'

export default function Footer({ className }) {
  return (
    <footer className={`${s.footer} ${className || ''}`}>
      <span>&copy; 2026 智能财税分析. All rights reserved.</span>
      <span>版本 v1.0.0 | 帮助中心 | 技术支持</span>
    </footer>
  )
}
