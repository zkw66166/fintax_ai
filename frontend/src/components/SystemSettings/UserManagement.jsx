import { useState, useEffect, useCallback } from 'react'
import {
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  fetchUserCompanies,
  updateUserCompanies,
  fetchAllCompanies,
  fetchCompaniesByRole,
} from '../../services/authApi'
import { ADMIN_ROLES, ROLE_LABELS, CREATABLE_ROLES } from '../../hooks/useAuth'
import { UserPlus } from 'lucide-react'
import s from './UserManagement.module.css'

const ROLE_BADGE_CLASS = {
  sys: s.badgeSys,
  admin: s.badgeAdmin,
  firm: s.badgeFirm,
  group: s.badgeGroup,
  enterprise: s.badgeEnterprise,
}

export default function UserManagement({ currentUser }) {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [modal, setModal] = useState(null) // null | {mode:'add'} | {mode:'edit',user} | {mode:'password',user}
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [error, setError] = useState('')

  const isAdmin = ADMIN_ROLES.includes(currentUser?.role)
  const isSys = currentUser?.role === 'sys'

  const load = useCallback(async () => {
    try {
      const list = await fetchUsers()
      setUsers(list)
    } catch {
      setError('加载用户列表失败')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = users.filter((u) => {
    if (search && !u.username.includes(search) && !(u.display_name || '').includes(search)) return false
    if (filterRole && u.role !== filterRole) return false
    if (filterStatus !== '' && String(u.is_active) !== filterStatus) return false
    return true
  })

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => ADMIN_ROLES.includes(u.role)).length,
  }

  const handleSave = async (formData) => {
    try {
      if (modal.mode === 'add') {
        await createUser(formData)
      } else if (modal.mode === 'password') {
        await updateUser(modal.user.id, { password: formData.password })
      } else {
        const payload = { ...formData }
        if (!payload.password) delete payload.password
        delete payload.username
        // 企业权限单独更新
        const companyIds = payload.company_ids
        delete payload.company_ids
        await updateUser(modal.user.id, payload)
        if (isAdmin && companyIds !== undefined) {
          await updateUserCompanies(modal.user.id, companyIds)
        }
      }
      setModal(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async () => {
    try {
      await deleteUser(confirmDelete.id)
      setConfirmDelete(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  // 可创建的角色列表
  const creatableRoles = CREATABLE_ROLES[currentUser?.role] || []
  // 角色筛选选项（非 sys 不显示 sys）
  const filterRoleOptions = isSys
    ? Object.entries(ROLE_LABELS)
    : Object.entries(ROLE_LABELS).filter(([k]) => k !== 'sys')

  return (
    <div className={s.wrap}>
      {error && (
        <div className={s.errorBar}>
          {error}
          <span className={s.errorClose} onClick={() => setError('')}>x</span>
        </div>
      )}

      <div className={s.statsRow}>
        <div className={s.statCard}>
          <div className={s.statNum}>{stats.total}</div>
          <div className={s.statLabel}>总用户数</div>
        </div>
        <div className={s.statCard}>
          <div className={s.statNum}>{stats.active}</div>
          <div className={s.statLabel}>活跃用户</div>
        </div>
        <div className={s.statCard}>
          <div className={s.statNum}>{stats.admins}</div>
          <div className={s.statLabel}>管理员</div>
        </div>
      </div>

      <div className={s.toolbar}>
        <input
          className={s.searchInput}
          placeholder="搜索用户名/显示名"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className={s.filterSelect} value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
          <option value="">全部角色</option>
          {filterRoleOptions.map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select className={s.filterSelect} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">全部状态</option>
          <option value="1">启用</option>
          <option value="0">禁用</option>
        </select>
        {creatableRoles.length > 0 && (
          <button className={s.addBtn} onClick={() => setModal({ mode: 'add' })}>
            <UserPlus size={14} className={s.addBtnIcon} /> 新增用户
          </button>
        )}
      </div>

      <table className={s.table}>
        <thead>
          <tr>
            <th>用户名</th><th>显示名</th><th>角色</th>
            <th>状态</th><th>创建时间</th><th>最后登录</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td>{u.display_name || '-'}</td>
              <td>
                <span className={`${s.badge} ${ROLE_BADGE_CLASS[u.role] || ''}`}>
                  {ROLE_LABELS[u.role] || u.role}
                </span>
              </td>
              <td><span className={u.is_active ? s.statusOn : s.statusOff}>{u.is_active ? '启用' : '禁用'}</span></td>
              <td>{u.created_at ? u.created_at.slice(0, 16).replace('T', ' ') : '-'}</td>
              <td>{u.last_login ? u.last_login.slice(0, 16).replace('T', ' ') : '-'}</td>
              <td className={s.actions}>
                {isAdmin ? (
                  <>
                    <button className={s.actionBtn} onClick={() => setModal({ mode: 'edit', user: u })}>编辑</button>
                    <button
                      className={`${s.actionBtn} ${s.deleteBtn}`}
                      onClick={() => setConfirmDelete(u)}
                      disabled={u.id === currentUser.id || u.role === 'sys'}
                    >
                      删除
                    </button>
                  </>
                ) : u.id === currentUser.id ? (
                  <button className={s.actionBtn} onClick={() => setModal({ mode: 'password', user: u })}>修改密码</button>
                ) : null}
              </td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={7} className={s.empty}>暂无数据</td></tr>
          )}
        </tbody>
      </table>

      {modal && (
        <UserModal
          mode={modal.mode}
          user={modal.user}
          currentUser={currentUser}
          isAdmin={isAdmin}
          onSave={handleSave}
          onClose={() => setModal(null)}
        />
      )}

      {confirmDelete && (
        <div className={s.overlay}>
          <div className={s.confirmBox}>
            <p>确定删除用户 <strong>{confirmDelete.username}</strong> 吗？</p>
            <div className={s.confirmActions}>
              <button className={s.cancelBtn} onClick={() => setConfirmDelete(null)}>取消</button>
              <button className={`${s.addBtn} ${s.deleteBtn}`} onClick={handleDelete}>确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function UserModal({ mode, user, currentUser, isAdmin, onSave, onClose }) {
  const creatableRoles = CREATABLE_ROLES[currentUser?.role] || []
  const [form, setForm] = useState({
    username: user?.username || '',
    password: '',
    role: user?.role || creatableRoles[0] || 'enterprise',
    display_name: user?.display_name || '',
    is_active: user?.is_active ?? 1,
    company_ids: [],
  })
  const [allCompanies, setAllCompanies] = useState([])

  // 初始化加载企业列表
  useEffect(() => {
    if (mode === 'password') return
    const initRole = user?.role || creatableRoles[0] || 'enterprise'

    const loadCompanies = async () => {
      try {
        if (isAdmin) {
          const all = await fetchAllCompanies()
          setAllCompanies(all)
          if (mode === 'add') {
            const defaults = await fetchCompaniesByRole(initRole)
            setForm(f => ({ ...f, company_ids: defaults.map(c => c.taxpayer_id) }))
          }
        } else {
          const defaults = await fetchCompaniesByRole(initRole)
          setAllCompanies(defaults)
          if (mode === 'add') {
            setForm(f => ({ ...f, company_ids: defaults.map(c => c.taxpayer_id) }))
          }
        }
        if (mode === 'edit' && user) {
          const res = await fetchUserCompanies(user.id)
          setForm(f => ({ ...f, company_ids: res.company_ids || [] }))
        }
      } catch {
        // 静默
      }
    }
    loadCompanies()
  }, [mode, user])

  // 角色切换时重新加载企业列表并自动全选
  const handleRoleChange = async (newRole) => {
    setForm(f => ({ ...f, role: newRole }))
    try {
      const defaults = await fetchCompaniesByRole(newRole)
      if (isAdmin) {
        setForm(f => ({ ...f, role: newRole, company_ids: defaults.map(c => c.taxpayer_id) }))
      } else {
        setAllCompanies(defaults)
        setForm(f => ({ ...f, role: newRole, company_ids: defaults.map(c => c.taxpayer_id) }))
      }
    } catch {
      if (!isAdmin) setAllCompanies([])
      setForm(f => ({ ...f, role: newRole, company_ids: [] }))
    }
  }

  const toggleCompany = (tid) => {
    setForm((f) => ({
      ...f,
      company_ids: f.company_ids.includes(tid)
        ? f.company_ids.filter((id) => id !== tid)
        : [...f.company_ids, tid],
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (mode === 'password') {
      onSave({ password: form.password })
      return
    }
    const data = { ...form }
    if (mode === 'edit' && !data.password) delete data.password
    if (mode === 'edit') delete data.username
    onSave(data)
  }

  const title = mode === 'add' ? '新增用户' : mode === 'password' ? '修改密码' : '编辑用户'

  return (
    <div className={s.overlay}>
      <div className={s.modalCard}>
        <h3 className={s.modalTitle}>{title}</h3>
        <form onSubmit={handleSubmit} className={s.modalForm}>
          {mode === 'password' ? (
            <label className={s.field}>
              <span>新密码</span>
              <input type="password" required minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </label>
          ) : (
            <>
              {mode === 'add' && (
                <label className={s.field}>
                  <span>用户名</span>
                  <input required minLength={2} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                </label>
              )}
              <label className={s.field}>
                <span>{mode === 'add' ? '密码' : '新密码（留空不修改）'}</span>
                <input type="password" minLength={mode === 'add' ? 6 : 0} required={mode === 'add'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </label>
              <label className={s.field}>
                <span>显示名</span>
                <input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
              </label>
              <label className={s.field}>
                <span>角色</span>
                <select value={form.role} onChange={(e) => handleRoleChange(e.target.value)}>
                  {creatableRoles.map((r) => (
                    <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                  ))}
                </select>
              </label>
              {isAdmin && (
                <label className={s.checkField}>
                  <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked ? 1 : 0 })} />
                  <span>启用账号</span>
                </label>
              )}
              {allCompanies.length > 0 && (
                <div className={s.companySection}>
                  <div className={s.companyLabel}>企业数据权限</div>
                  <div className={s.companyList}>
                    {allCompanies.map((c) => (
                      <label key={c.taxpayer_id} className={s.companyItem}>
                        <input
                          type="checkbox"
                          checked={form.company_ids.includes(c.taxpayer_id)}
                          onChange={() => toggleCompany(c.taxpayer_id)}
                        />
                        <span>{c.taxpayer_name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          <div className={s.modalActions}>
            <button type="button" className={s.cancelBtn} onClick={onClose}>取消</button>
            <button type="submit" className={s.addBtn}>保存</button>
          </div>
        </form>
      </div>
    </div>
  )
}
