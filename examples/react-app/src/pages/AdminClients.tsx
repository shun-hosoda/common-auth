import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type AdminClient,
  type CreateClientInput,
  listClients,
  createClient,
} from '../api/adminApi'

// ─── Modal styles ─────────────────────────────────────────────────────────────

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

// ─── Component ────────────────────────────────────────────────────────────────

interface CreateForm {
  clientId: string
  name: string
}

const emptyForm = (): CreateForm => ({ clientId: '', name: '' })

export default function AdminClients() {
  const { user, logout, getAccessToken } = useAuth()
  const navigate = useNavigate()

  const profile = user?.profile as Record<string, unknown> | undefined
  const adminEmail = profile?.email as string || ''

  const [clients, setClients] = useState<AdminClient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<CreateForm>(emptyForm())
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const loaded = useRef(false)

  // ── fetch ──────────────────────────────────────────────────────────────────
  const fetchClients = async () => {
    const token = getAccessToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      setClients(await listClients(token))
    } catch (e) {
      setError(e instanceof Error ? e.message : '読み込みに失敗しました')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
    fetchClients()
  }, [])

  // ── create ─────────────────────────────────────────────────────────────────
  const handleCreate = async () => {
    if (!form.clientId.trim()) {
      setCreateError('クライアントIDは必須です')
      return
    }
    const token = getAccessToken()
    if (!token) return
    setCreating(true)
    setCreateError(null)
    try {
      const input: CreateClientInput = {
        clientId: form.clientId.trim(),
        name: form.name.trim() || undefined,
      }
      await createClient(token, input)
      setShowCreate(false)
      setForm(emptyForm())
      await fetchClients()
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : '作成に失敗しました')
    } finally {
      setCreating(false)
    }
  }

  // ── filter ─────────────────────────────────────────────────────────────────
  const filtered = clients.filter((c) => {
    const q = search.toLowerCase()
    return (
      c.clientId.toLowerCase().includes(q) ||
      (c.name ?? '').toLowerCase().includes(q)
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
          <button className="btn btn-secondary" onClick={logout}
            style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>
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
            <h1 style={{ margin: 0, flex: 1 }}>🏢 テナント管理</h1>
            <button className="btn btn-primary" onClick={() => { setForm(emptyForm()); setCreateError(null); setShowCreate(true) }}>
              + テナント追加
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="section">
          <input
            type="text"
            placeholder="クライアントID・名前で検索..."
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
              <button className="btn btn-secondary" onClick={fetchClients}
                style={{ marginLeft: '1rem', fontSize: '0.875rem', padding: '0.3rem 0.6rem' }}>
                再試行
              </button>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--border)' }}>
                    {['クライアントID', '表示名', 'ステータス'].map((h) => (
                      <th key={h} style={{
                        padding: '0.75rem 1rem', textAlign: 'left',
                        fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.05em',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={3} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        テナントが見つかりません
                      </td>
                    </tr>
                  ) : filtered.map((c) => (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <code style={{ fontSize: '0.85rem', background: 'var(--bg)', padding: '0.2rem 0.5rem', borderRadius: 4 }}>
                          {c.clientId}
                        </code>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                        {c.name ?? '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          display: 'inline-block', padding: '0.2rem 0.6rem', borderRadius: 9999,
                          fontSize: '0.75rem', fontWeight: 600,
                          background: c.enabled ? '#dcfce7' : '#fee2e2',
                          color: c.enabled ? '#15803d' : '#b91c1c',
                        }}>
                          {c.enabled ? '有効' : '無効'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ padding: '0.5rem 1rem', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {filtered.length} 件 / 全 {clients.length} 件
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Create Modal ──────────────────────────────────────────────────── */}
      {showCreate && (
        <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) setShowCreate(false) }}>
          <div style={modalBox}>
            <h2 style={{ margin: '0 0 1.5rem 0' }}>テナント追加</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                  クライアントID <span style={{ color: 'var(--danger)' }}>*</span>
                </span>
                <input
                  type="text"
                  value={form.clientId}
                  onChange={(e) => setForm((f) => ({ ...f, clientId: e.target.value }))}
                  placeholder="example-corp"
                  style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  英数字・ハイフンのみ。後から変更できません。
                </span>
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>表示名</span>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Example Corporation"
                  style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, fontSize: '1rem' }}
                />
              </label>
              {createError && (
                <div style={{ color: 'var(--danger)', fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>
                  {createError}
                </div>
              )}
            </div>
            <div className="btn-group" style={{ marginTop: '1.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)} disabled={creating}>
                キャンセル
              </button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={creating}>
                {creating ? '作成中...' : '追加する'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
