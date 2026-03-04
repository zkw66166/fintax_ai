import { useState, useCallback, useEffect } from 'react'
import { fetchCurrentUser } from '../services/authApi'

const ADMIN_ROLES = ['sys', 'admin']
const ROLE_LABELS = {
  sys: '超级管理员',
  admin: '系统管理员',
  firm: '事务所用户',
  group: '集团企业用户',
  enterprise: '普通企业用户',
}
const CREATABLE_ROLES = {
  sys: ['admin', 'firm', 'group', 'enterprise'],
  admin: ['admin', 'firm', 'group', 'enterprise'],
  firm: ['firm', 'enterprise'],
  group: ['group', 'enterprise'],
  enterprise: ['enterprise'],
}

export { ADMIN_ROLES, ROLE_LABELS, CREATABLE_ROLES }

export default function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    fetchCurrentUser()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
      })
      .finally(() => setLoading(false))
  }, [])

  const handleLogin = useCallback((token, userInfo) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(userInfo))
    setUser(userInfo)
  }, [])

  const handleLogout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }, [])

  const role = user?.role || ''

  return {
    user,
    loading,
    handleLogin,
    handleLogout,
    isAdmin: ADMIN_ROLES.includes(role),
    isSys: role === 'sys',
    canEditSettings: ADMIN_ROLES.includes(role),
    roleLabel: ROLE_LABELS[role] || '用户',
    creatableRoles: CREATABLE_ROLES[role] || [],
  }
}
