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
  resetMfa,
} from '../api/adminApi'

// ─── Design tokens ──────────────────────────────────────────────────────────
const tk = {
  primary:     '#2563eb',
  bg:          '#f8fafc',
  surface:     '#ffffff',
  border:      '#e2e8f0',
  text:        '#1e293b',
  textMuted:   '#64748b',
  textInverse: '#ffffff',
  radiusMd:    '8px',
  radiusLg:    '12px',
  radiusFull:  '9999px',
  shadowSm:    '0 1px 2px 0 rgb(0 0 0 / 0.06)',
  shadowMd:    '0 4px 12px 0 rgb(0 0 0 / 0.10)',
}

// ─── Modal ────────────────────────────────────────────────────────────────────

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 1000,
}
const modalBox: React.CSSProperties = {
  background: tk.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 480,
  boxShadow: tk.shadowMd,
}
const mfaModalBox: React.CSSProperties = {
  background: tk.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 400,
  boxShadow: tk.shadowMd,
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

  const isSuperAdmin  = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin       = isSuperAdmin || isTenantAdmin
  const profile       = user?.profile as Record<string, unknown> | undefined
  const adminEmail    = profile?.email as string | undefined ?? ''
  const adminInitial  = adminEmail.charAt(0).toUpperCase() || '?'

  const rawTenantId = profile?.tenant_id
  const tenantName  = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) ?? ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

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

  const [mfaTarget,  setMfaTarget]  = useState<AdminUser | null>(null)
  const [mfaLoading, setMfaLoading] = useState(false)

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

  // ── MFA reset ──────────────────────────────────────────────────────────────
  const handleMfaReset = async () => {
    if (!mfaTarget) return
    const token = getAccessToken()
    if (!token) return
    setMfaLoading(true)
    try {
      await resetMfa(token, mfaTarget.id)
      setMfaTarget(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'MFAリセットに失敗しました')
    } finally {
      setMfaLoading(false)
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
  const navItems = [
    { label: 'ダッシュボード', icon: '🏠', path: '/dashboard' },
    ...(isAdmin      ? [{ label: 'ユーザー管理', icon: '👥', path: '/admin/users' }] : []),
    ...(isSuperAdmin ? [{ label: 'テナント管理', icon: '🏢', path: '/admin/clients' }] : []),
  ]

  return (
    <div style={{ minHeight: '100vh', background: tk.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>

      {/* ── TopBar ── */}
      <header style={{
        height: 60, background: tk.surface,
        borderBottom: `1px solid ${tk.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 16px', position: 'sticky', top: 0, zIndex: 100,
        boxShadow: tk.shadowSm,
      }}>
        <span style={{ fontSize: '1rem', fontWeight: 700, color: tk.text }}>{tenantTitle}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 32, height: 32, borderRadius: tk.radiusFull,
            background: tk.primary, color: tk.textInverse,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: '0.875rem',
          }}>
            {adminInitial}
          </div>
          <span style={{ fontSize: '0.875rem', color: tk.text, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {adminEmail}
          </span>
          <button onClick={logout} style={{
            padding: '6px 12px', borderRadius: tk.radiusMd,
            background: 'none', border: `1px solid ${tk.border}`,
            fontSize: '0.8rem', cursor: 'pointer', color: tk.text,
          }}>ログアウト</button>
        </div>
      </header>

      {/* ── Body ── */}
      <div style={{ display: 'flex' }}>

        {/* SideNav */}
        <nav aria-label="サイドメニュー" style={{
          width: 220, flexShrink: 0,
          background: tk.surface, borderRight: `1px solid ${tk.border}`,
          padding: '16px 8px', minHeight: 'calc(100vh - 60px)',
        }}>
          {navItems.map(item => {
            const active = item.path === '/admin/users'
            return (
              <button key={item.path} onClick={() => navigate(item.path)}
                aria-current={active ? 'page' : undefined}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '10px 12px', borderRadius: tk.radiusMd,
                  background: active ? '#dbeafe' : 'none',
                  color: active ? tk.primary : tk.text,
                  border: 'none', cursor: 'pointer', textAlign: 'left',
                  fontSize: '0.875rem', fontWeight: active ? 600 : 400,
                  marginBottom: 2, minHeight: 44,
                }}
              >
                <span aria-hidden="true" style={{ fontSize: '1rem' }}>{item.icon}</span>
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* Main */}
        <main style={{ flex: 1, minWidth: 0, padding: '24px' }}>

          {/* Page header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '20px', flexWrap: 'wrap' }}>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: tk.text, flex: 1 }}>
              👥 ユーザー管理
              {isSuperAdmin && (
                <span style={{ fontSize: '0.875rem', fontWeight: 400, color: tk.textMuted, marginLeft: '0.5rem' }}>
                  — 全テナント
                </span>
              )}
            </h1>
            <button
              onClick={() => { setCreateForm(emptyCreate()); setCreateError(null); setShowCreate(true) }}
              style={{
                padding: '8px 16px', borderRadius: tk.radiusMd,
                background: tk.primary, color: tk.textInverse,
                border: 'none', cursor: 'pointer',
                fontSize: '0.875rem', fontWeight: 600,
              }}
            >
              + ユーザー追加
            </button>
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="名前・メールで検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '8px 12px',
              border: `1px solid ${tk.border}`, borderRadius: tk.radiusMd,
              fontSize: '0.9rem', boxSizing: 'border-box',
              marginBottom: '16px', outline: 'none',
            }}
          />
          {/* Table */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: tk.textMuted }}>読み込み中...</div>
          ) : error ? (
            <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '1rem', borderRadius: tk.radiusMd, display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <strong>エラー:</strong> {error}
              <button onClick={fetchUsers} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #b91c1c', background: 'none', color: '#b91c1c', cursor: 'pointer', fontSize: '0.8rem' }}>
                再試行
              </button>
            </div>
          ) : (
            <div style={{ background: tk.surface, border: `1px solid ${tk.border}`, borderRadius: tk.radiusLg, overflow: 'hidden', boxShadow: tk.shadowSm }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: tk.bg }}>
                    {['ユーザー', 'メール', 'テナント', 'ステータス', '操作'].map((h) => (
                      <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 600, color: tk.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: `1px solid ${tk.border}` }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: tk.textMuted }}>ユーザーが見つかりません</td></tr>
                  ) : filtered.map((u, idx) => {
                    const name = [u.firstName, u.lastName].filter(Boolean).join(' ') || u.username
                    const initial = name.charAt(0).toUpperCase()
                    const tId = u.attributes?.tenant_id?.[0] ?? '—'
                    return (
                      <tr key={u.id} style={{ borderBottom: idx < filtered.length - 1 ? `1px solid ${tk.border}` : 'none' }}>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ width: 36, height: 36, borderRadius: tk.radiusFull, background: tk.primary, color: tk.textInverse, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem', flexShrink: 0 }}>
                              {initial}
                            </div>
                            <span style={{ fontWeight: 500, fontSize: '0.9rem', color: tk.text }}>{name}</span>
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px', color: tk.textMuted, fontSize: '0.875rem' }}>{u.email}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <code style={{ fontSize: '0.78rem', background: tk.bg, padding: '2px 7px', borderRadius: 4, border: `1px solid ${tk.border}` }}>{tId}</code>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-block', padding: '3px 10px', borderRadius: tk.radiusFull,
                            fontSize: '0.75rem', fontWeight: 600,
                            background: u.enabled ? '#dcfce7' : '#fee2e2',
                            color:      u.enabled ? '#15803d' : '#b91c1c',
                          }}>
                            {u.enabled ? '有効' : '無効'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {/* 編集 */}
                            <button onClick={() => openEdit(u)} style={{ padding: '4px 10px', borderRadius: tk.radiusMd, border: 'none', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 500, background: tk.bg, color: tk.text }}>編集</button>
                            {/* 有効/無効 */}
                            <button onClick={() => toggleEnabled(u)} style={{ padding: '4px 10px', borderRadius: tk.radiusMd, border: 'none', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 500, background: u.enabled ? '#fee2e2' : '#dcfce7', color: u.enabled ? '#b91c1c' : '#15803d' }}>
                              {u.enabled ? '無効化' : '有効化'}
                            </button>
                            {/* MFA リセット */}
                            <button onClick={() => setMfaTarget(u)} style={{ padding: '4px 10px', borderRadius: tk.radiusMd, border: 'none', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 500, background: '#fef3c7', color: '#92400e' }}>MFAリセット</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div style={{ padding: '8px 16px', borderTop: `1px solid ${tk.border}`, fontSize: '0.78rem', color: tk.textMuted }}>
                {filtered.length} 件 / 全 {users.length} 件
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── MFA Reset Confirm Modal ─────────────────────────────────────────── */}
      {mfaTarget && (
        <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget && !mfaLoading) setMfaTarget(null) }}>
          <div style={mfaModalBox}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔐</div>
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem' }}>MFA 設定をリセット</h2>
              <p style={{ margin: 0, color: tk.textMuted, fontSize: '0.875rem', lineHeight: 1.6 }}>
                <strong>{[mfaTarget.firstName, mfaTarget.lastName].filter(Boolean).join(' ') || mfaTarget.email}</strong> の
                MFA（二要素認証）設定を削除します。<br />
                次回ログイン時にMFAを再設定するよう求められます。
              </p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setMfaTarget(null)} disabled={mfaLoading}
                style={{ padding: '8px 16px', borderRadius: tk.radiusMd, background: 'none', border: `1px solid ${tk.border}`, fontSize: '0.875rem', cursor: mfaLoading ? 'not-allowed' : 'pointer', color: tk.text, opacity: mfaLoading ? 0.5 : 1 }}>
                キャンセル
              </button>
              <button onClick={handleMfaReset} disabled={mfaLoading}
                style={{ padding: '8px 20px', borderRadius: tk.radiusMd, background: '#f59e0b', color: tk.textInverse, border: 'none', cursor: mfaLoading ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: mfaLoading ? 0.6 : 1 }}>
                {mfaLoading ? 'リセット中...' : 'リセットする'}
              </button>
            </div>
          </div>
        </div>
      )}

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
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setShowCreate(false)} disabled={creating}
                style={{ padding: '8px 16px', borderRadius: tk.radiusMd, background: 'none', border: `1px solid ${tk.border}`, fontSize: '0.875rem', cursor: creating ? 'not-allowed' : 'pointer', color: tk.text, opacity: creating ? 0.5 : 1 }}>キャンセル</button>
              <button onClick={handleCreate} disabled={creating}
                style={{ padding: '8px 20px', borderRadius: tk.radiusMd, background: tk.primary, color: tk.textInverse, border: 'none', cursor: creating ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: creating ? 0.6 : 1 }}>
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
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setEditTarget(null)} disabled={saving}
                style={{ padding: '8px 16px', borderRadius: tk.radiusMd, background: 'none', border: `1px solid ${tk.border}`, fontSize: '0.875rem', cursor: saving ? 'not-allowed' : 'pointer', color: tk.text, opacity: saving ? 0.5 : 1 }}>キャンセル</button>
              <button onClick={handleSave} disabled={saving}
                style={{ padding: '8px 20px', borderRadius: tk.radiusMd, background: tk.primary, color: tk.textInverse, border: 'none', cursor: saving ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
                {saving ? '保存中...' : '保存する'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
