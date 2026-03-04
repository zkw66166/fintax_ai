import { useState } from 'react'
import { login } from '../../services/authApi'
import s from './Login.module.css'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(username, password)
      onLogin(data.access_token, data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={s.page}>
      <div className={s.card}>
        <div className={s.logo}>FT</div>
        <h1 className={s.title}>智能财税咨询系统</h1>
        <p className={s.subtitle}>
          ENTERPRISE FINANCIAL &amp; TAX INTELLIGENCE
        </p>
        <form onSubmit={handleSubmit} className={s.form}>
          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={s.input}
            autoFocus
            required
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={s.input}
            required
          />
          {error && <div className={s.error}>{error}</div>}
          <button type="submit" className={s.btn} disabled={loading}>
            {loading ? '登录中...' : '登 录'}
          </button>
        </form>
        <div className={s.hint}>
          测试账号: admin / admin123 或 user1 / 123456
        </div>
      </div>
    </div>
  )
}