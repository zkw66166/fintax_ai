import { useState } from 'react'
import { verifyCaptcha } from '../../services/authApi'
import s from './CaptchaModal.module.css'

export default function CaptchaModal({ onVerified }) {
  const [input, setInput] = useState('')
  const [attempts, setAttempts] = useState(0)
  const [error, setError] = useState('')
  const [locked, setLocked] = useState(false)
  const [loading, setLoading] = useState(false)

  const MAX_ATTEMPTS = 3

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (locked || loading) return

    setLoading(true)
    setError('')

    try {
      const result = await verifyCaptcha(input)

      if (result.success) {
        onVerified()
      } else {
        const newAttempts = attempts + 1
        setAttempts(newAttempts)

        if (newAttempts >= MAX_ATTEMPTS) {
          setLocked(true)
          setError(`验证失败，已达到最大尝试次数（${MAX_ATTEMPTS}次）。请刷新页面重试。`)
        } else {
          setError(`验证码错误，还剩 ${MAX_ATTEMPTS - newAttempts} 次机会`)
        }

        setInput('')
      }
    } catch (err) {
      setError(err.message || '验证失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={s.overlay}>
      <div className={s.modal}>
        <h2 className={s.title}>访问验证</h2>
        <p className={s.description}>请输入验证码以继续</p>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            className={s.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="请输入验证码"
            disabled={locked}
            autoFocus
          />

          {error && <div className={s.error}>{error}</div>}

          <button
            type="submit"
            className={s.btn}
            disabled={locked || loading || !input.trim()}
          >
            {locked ? '已锁定' : loading ? '验证中...' : '验证'}
          </button>
        </form>

        <div className={s.hint}>
          剩余尝试次数: {MAX_ATTEMPTS - attempts}
        </div>
      </div>
    </div>
  )
}
