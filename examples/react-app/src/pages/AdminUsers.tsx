import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type AdminUser,
  type CreateUserInput,
  type UpdateUserInput,
  listUsers,
  createUser,
  updateUser,
  disableUser,
  resetPassword,
} from '../api/adminApi'

// ─── Modal ────────────────────────────────────────────────────────────────────

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 1000,
}
const modalBox: React.CSSProperties = {
  background: '#fff', borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 480,
  boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface CreateForm {
  email: string; firstName: string; lastName: string
  password: string; temporary: boolean
}
interface EditForm {
  firstName: string; lastName: string; email: string
  newPassword: string; resetPassword: boolean
}

const emptyCreate = (): CreateForm => ({
  email: '', firstName: '', lastName: '', password: '', temporary: true,
})
const toEditForm = (u: AdminUser): EditForm => ({
  firstName: u.firstName ?? '',
  lastName: u.lastName ?? '',
  email: u.email,
  newPassword: '',
  resetPassword: false,
})

// ─── Component ────────────────────────────────────────────────────────────────

export default function AdminUsers() {
  const { user, logout, hasRole, getAccessToken } = useAuth()
  const navigate = useNavigate()

  const isSuperAdmin = hasRole('super_admin')
  const profile = user?.profile as Record<string, unknown> | undefined
  const adminEmail = profile?.email as string || ''

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate())
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const [editTarget, setEditTarget] = useState<AdminUser | null>(null)
  const [editForm, setEditForm] = useState<EditForm | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const loaded = useRef(false)

  // ── fetch ──────────────────────────────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    const token = getAccessToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      setUsers(await listUsers(token))
    } catch (e) {
      setError(e instanceof Error ? e.message : '読み込みに失敗しました')
    } finally {
      setLoading(false)
    }
  }, [getAccessToken])

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
    fetchUsers()
  }, [fetchUsers])

  // ── create ─────────────────────────────────────────────────────────────────
  const handleCreate = async () => {
    const token = getAccessToken()
    if (!token) return
    if (!createForm.email || !createForm.password) {
      setCreateError('メールアドレスとパスワードは必須です')
      return
    }
    setCreating(true)
    setCreateError(null)
    try {
      const input: CreateUserInput = {
        email: createForm.email,
        firstName: createForm.firstName || undefined,
        lastName: createForm.lastName || undefined,
        password: createForm.password,
        temporary: createForm.temporary,
      }
      await createUser(token, input)
      setShowCreate(false)
      setCreateForm(emptyCreate())
      await fetchUsers()
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : '作成に失敗しました')
    } finally {
      setCreating(false)
    }
  }

  // ── edit ───────────────────────────────────────────────────────────────────
  const openEdit = (u: AdminUser) => {
    setEditTarget(u)
    setEditForm(toEditForm(u))
    setEditError(null)
  }

  const handleSave = async () => {
    if (!editTarget || !editForm) return
    const token = getAccessToken()
    if (!token) return
    setSaving(true)
    setEditError(null)
    try {
      const upd: UpdateUserInput = {
        firstName: editForm.firstName,
        lastName: editForm.lastName,
        email: editForm.email,
      }
      await updateUser(token, editTarget.id, upd)

      if (editForm.resetPassword && editForm.newPassword) {
        await resetPassword(token, editTarget.id, editForm.newPassword, true)
      }

      setEditTarget(null)
      setEditForm(null)
      await fetchUsers()
    } catch (e) {
      setEditError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  // ── toggle enabled ─────────────────────────────────────────────────────────
  const toggleEnabled = async (u: AdminUser) => {
    const token = getAccessToken()
    if (!token) return
    try {
      if (u.enabled) {
        await disableUser(token, u.id)
      } else {
        await updateUser(token, u.id, { enabled: true })
      }
      setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, enabled: !u.enabled } : x))
    } catch {
      alert('ステータス変更に失敗しました')
    }
  }

  // ── filter ─────────────────────────────────────────────────────────────────
  const filtered = users.filter((u) => {
    const q = search.toLowerCase()
    return (
      u.email.toLowerCase().includes(q) ||
      (u.firstName ?? '').toLowerCase().includes(q) ||
      (u.lastName ?? '').toLowerCase().includes(q)
    )
  })

  // ─── render ────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* Nav */}
      <nav className="nav">
        <div className="nav-brand">🔐 Common Auth</div>
        <div className="user-info">
          <span>{adminEmail}</span>
          <button className="btn btn-secondary" onClick={logout} style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>
            ログアウト
          </button>
        </div>
      </nav>

      <div className="container">
        {/* Header */}
        <div className="section">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}
              style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>
              ← ダッシュボード
            </button>
            <h1 style={{ margin: 0, flex: 1 }}>
              👥 ユーザー管理
              {isSuperAdmin && (
                <span style={{ fontSize: '0.875rem', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                  — 全テナント
                </span>
              )}
            </h1>
            <button className="btn btn-primary" onClick={() => { setCreateForm(emptyCreate()); setCreateError(null); setShowCreate(true) }}>
              + ユーザー追加
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="section">
          <input
            type="text"
            placeholder="名前・メールで検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '0.625rem 1rem',
              border: '1px solid var(--border)', borderRadius: 8,
              fontSize: '1rem', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Table */}
        <div className="section">
          {loading ? (
            <div className="loading" style={{ height: 200 }}>読み込み中...</div>
          ) : error ? (
            <div className="card" style={{ color: 'var(--danger)' }}>
              <strong>エラー:</strong> {error}
              <button className="btn btn-secondary" onClick={fetchUsers} style={{ marginLeft: '1rem', fontSize: '0.875rem', padding: '0.3rem 0.6rem' }}>
                再試行
              </button>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--border)' }}>
                    {['ユーザー', 'メール', 'テナント', 'ステータス', '操作'].map((h) => (
                      <th key={h} style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>ユーザーが見つかりません</td></tr>
                  ) : filtered.map((u) => {
                    const name = [u.firstName, u.lastName].filter(Boolean).join(' ') || u.username
                    const initial = name.charAt(0).toUpperCase()
                    const tId = u.attributes?.tenant_id?.[0] ?? '—'
                    return (
                      <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '0.875rem', flexShrink: 0 }}>
                              {initial}
                            </div>
                            <span style={{ fontWeight: 500 }}>{name}</span>
                          </div>
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>{u.email}</td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <code style={{ fontSize: '0.8rem', background: 'var(--bg)', padding: '0.2rem 0.4rem', borderRadius: 4 }}>{tId}</code>
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <span style={{
                            display: 'inline-block', padding: '0.2rem 0.6rem', borderRadius: 9999,
                            fontSize: '0.75rem', fontWeight: 600,
                            background: u.enabled ? '#dcfce7' : '#fee2e2',
                            color: u.enabled ? '#15803d' : '#b91c1c',
                          }}>
                            {u.enabled ? '有効' : '無効'}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <button className="btn btn-secondary" onClick={() => openEdit(u)}
                              style={{ fontSize: '0.8rem', padding: '0.3rem 0.7rem' }}>
                              編集
                            </button>
                            <button
                              onClick={() => toggleEnabled(u)}
                              style={{
                                fontSize: '0.8rem', padding: '0.3rem 0.7rem',
                                border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 500,
                                background: u.enabled ? '#fee2e2' : '#dcfce7',
                                color: u.enabled ? '#b91c1c' : '#15803d',
                              }}>
                              {u.enabled ? '無効化' : '有効化'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div style={{ padding: '0.5rem 1rem', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {filtered.length} 件 / 全 {users.length} 件
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Create Modal ──────────────────────────────────────────────────── */}
      {showCreate && (
        <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) setShowCreate(false) }}>
          <div style={modalBox}>
            <h2 style={{ margin: '0 0 1.5rem 0' }}>ユーザー追加</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>メールアドレス <span style={{ color: 'var(--danger)' }}>*</span></span>
                <input type="email" value={createForm.email} onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="user@example.com"
                  style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
              </label>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>姓</span>
                  <input type="text" value={createForm.lastName} onChange={(e) => setCreateForm((f) => ({ ...f, lastName: e.target.value }))}
                    placeholder="山田"
                    style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
                </label>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>名</span>
                  <input type="text" value={createForm.firstName} onChange={(e) => setCreateForm((f) => ({ ...f, firstName: e.target.value }))}
                    placeholder="太郎"
                    style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
                </label>
              </div>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>初期パスワード <span style={{ color: 'var(--danger)' }}>*</span></span>
                <input type="password" value={createForm.password} onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  placeholder="8文字以上"
                  style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={createForm.temporary} onChange={(e) => setCreateForm((f) => ({ ...f, temporary: e.target.checked }))} />
                <span style={{ fontSize: '0.875rem' }}>一時パスワード（初回ログイン時に変更を要求）</span>
              </label>
              {createError && <div style={{ color: 'var(--danger)', fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>{createError}</div>}
            </div>
            <div className="btn-group" style={{ marginTop: '1.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)} disabled={creating}>キャンセル</button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={creating}>
                {creating ? '作成中...' : '追加する'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit Modal ────────────────────────────────────────────────────── */}
      {editTarget && editForm && (
        <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) setEditTarget(null) }}>
          <div style={modalBox}>
            <h2 style={{ margin: '0 0 1.5rem 0' }}>ユーザー編集</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>メールアドレス</span>
                <input type="email" value={editForm.email} onChange={(e) => setEditForm((f) => f && ({ ...f, email: e.target.value }))}
                  style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
              </label>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>姓</span>
                  <input type="text" value={editForm.lastName} onChange={(e) => setEditForm((f) => f && ({ ...f, lastName: e.target.value }))}
                    style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
                </label>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>名</span>
                  <input type="text" value={editForm.firstName} onChange={(e) => setEditForm((f) => f && ({ ...f, firstName: e.target.value }))}
                    style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }} />
                </label>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.75rem' }}>
                  <input type="checkbox" checked={editForm.resetPassword} onChange={(e) => setEditForm((f) => f && ({ ...f, resetPassword: e.target.checked }))} />
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>パスワードをリセットする</span>
                </label>
                {editForm.resetPassword && (
                  <input type="password" value={editForm.newPassword} onChange={(e) => setEditForm((f) => f && ({ ...f, newPassword: e.target.value }))}
                    placeholder="新しいパスワード"
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                )}
              </div>
              {editError && <div style={{ color: 'var(--danger)', fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>{editError}</div>}
            </div>
            <div className="btn-group" style={{ marginTop: '1.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setEditTarget(null)} disabled={saving}>キャンセル</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? '保存中...' : '保存する'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
