const BASE = '/api'

function authHeaders(extra = {}) {
  const token = localStorage.getItem('access_token')
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function login(username, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '登录失败')
  }
  return res.json()
}

export async function fetchCurrentUser() {
  const res = await fetch(`${BASE}/auth/me`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('认证失败')
  return res.json()
}

export async function fetchUsers() {
  const res = await fetch(`${BASE}/users`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '获取用户列表失败')
  }
  return res.json()
}

export async function createUser(data) {
  const res = await fetch(`${BASE}/users`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error(e.detail || '创建用户失败')
  }
  return res.json()
}

export async function updateUser(userId, data) {
  const res = await fetch(`${BASE}/users/${userId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error(e.detail || '更新用户失败')
  }
  return res.json()
}

export async function deleteUser(userId) {
  const res = await fetch(`${BASE}/users/${userId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error(e.detail || '删除用户失败')
  }
  return res.json()
}

export async function fetchUserCompanies(userId) {
  const res = await fetch(`${BASE}/users/${userId}/companies`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('获取用户企业权限失败')
  return res.json()
}

export async function updateUserCompanies(userId, companyIds) {
  const res = await fetch(`${BASE}/users/${userId}/companies`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ company_ids: companyIds }),
  })
  if (!res.ok) throw new Error('更新用户企业权限失败')
  return res.json()
}

export async function fetchAllCompanies() {
  const res = await fetch(`${BASE}/companies`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('获取企业列表失败')
  return res.json()
}

export async function fetchCompaniesByRole(role) {
  const res = await fetch(`${BASE}/companies/by-role/${role}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('获取角色默认企业失败')
  return res.json()
}

export async function verifyCaptcha(code) {
  const res = await fetch(`${BASE}/auth/captcha/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '验证失败')
  }
  return res.json()
}
