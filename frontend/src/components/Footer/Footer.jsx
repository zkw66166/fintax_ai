import s from './Footer.module.css'

export default function Footer({ className }) {
  return (
    <footer className={`${s.footer} ${className || ''}`}>
      <span>&copy; 2026 慧经盈智能科技. All rights reserved.</span>
      <span>版本 v1.0.0 | 帮助中心 | 技术支持</span>
    </footer>
  )
}
