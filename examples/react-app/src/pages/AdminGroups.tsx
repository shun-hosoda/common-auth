import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type Group,
  type GroupMember,
  type EnrichedUser,
  listGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  listGroupMembers,
  addGroupMembers,
  removeGroupMember,
  listUsersWithGroups,
} from '../api/adminApi'
import { t } from '../theme/tokens'
import {
  useIsMobile,
  UserDropdown,
  SideNav,
  MobileDrawer,
  type DropdownItem,
  type NavItem,
} from '../components/layout'
import {
  MdHome, MdPeople, MdLock, MdBusiness, MdManageAccounts, MdLogout,
  MdGroup, MdAdd, MdEdit, MdDelete, MdPersonAdd, MdPersonRemove,
  MdHistory,
} from 'react-icons/md'

// ─── Styles ───────────────────────────────────────────────────────────────────

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 1000,
}
const modalBox: React.CSSProperties = {
  background: t.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 480, boxShadow: t.shadowMd,
}
const membersModalBox: React.CSSProperties = {
  background: t.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 640, maxHeight: '80vh', overflow: 'auto',
  boxShadow: t.shadowMd,
}

const btnBase: React.CSSProperties = {
  border: 'none', borderRadius: t.radiusMd, cursor: 'pointer',
  fontWeight: 600, fontSize: '0.875rem', padding: '8px 16px',
  display: 'inline-flex', alignItems: 'center', gap: 6,
}
const btnPrimary: React.CSSProperties = {
  ...btnBase, background: t.primary, color: '#fff',
}
const btnGhost: React.CSSProperties = {
  ...btnBase, background: 'transparent', color: t.textMuted,
  border: `1px solid ${t.border}`,
}
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px',
  border: `1px solid ${t.border}`, borderRadius: t.radiusMd,
  fontSize: '0.9rem', color: t.text, boxSizing: 'border-box',
}

// ─── GroupFormModal ───────────────────────────────────────────────────────────

function GroupFormModal({
  group,
  onSave,
  onClose,
}: {
  group?: Group
  onSave: (name: string, description: string) => Promise<void>
  onClose: () => void
}) {
  const [name, setName] = useState(group?.name ?? '')
  const [description, setDescription] = useState(group?.description ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!name.trim()) { setError('グループ名は必須です'); return }
    setSaving(true)
    setError(null)
    try {
      await onSave(name.trim(), description.trim())
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modalBox} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 1.5rem', color: t.text }}>
          {group ? 'グループ編集' : 'グループ作成'}
        </h3>
        {error && (
          <p style={{ color: t.danger, fontSize: '0.875rem', marginBottom: 12 }}>{error}</p>
        )}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: '0.875rem' }}>
            グループ名 <span style={{ color: t.danger }}>*</span>
          </label>
          <input
            style={inputStyle}
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="例: 開発チーム"
            disabled={saving}
          />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: '0.875rem' }}>
            説明
          </label>
          <textarea
            style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="グループの説明（省略可）"
            disabled={saving}
          />
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button style={btnGhost} onClick={onClose} disabled={saving}>キャンセル</button>
          <button style={btnPrimary} onClick={handleSubmit} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── MembersModal ─────────────────────────────────────────────────────────────

function MembersModal({
  group,
  token,
  allUsers,
  onClose,
}: {
  group: Group
  token: string
  allUsers: EnrichedUser[]
  onClose: () => void
}) {
  const [members, setMembers] = useState<GroupMember[]>([])
  const [loading, setLoading] = useState(true)
  const [addMode, setAddMode] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMembers = useCallback(async () => {
    try {
      const res = await listGroupMembers(token, group.id)
      setMembers(res.members)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'メンバー取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [token, group.id])

  useEffect(() => { fetchMembers() }, [fetchMembers])

  const memberIds = new Set(members.map(m => m.user_id))
  const addableUsers = allUsers.filter(u => !memberIds.has(u.id))

  const handleAdd = async () => {
    if (!selectedUserId) return
    setSaving(true)
    setError(null)
    try {
      await addGroupMembers(token, group.id, [selectedUserId])
      setSelectedUserId('')
      setAddMode(false)
      await fetchMembers()
    } catch (e) {
      setError(e instanceof Error ? e.message : '追加に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async (userId: string) => {
    if (!window.confirm('このメンバーをグループから削除しますか？')) return
    setSaving(true)
    setError(null)
    try {
      await removeGroupMember(token, group.id, userId)
      await fetchMembers()
    } catch (e) {
      setError(e instanceof Error ? e.message : '削除に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={membersModalBox} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 0.25rem', color: t.text }}>
          <MdGroup style={{ verticalAlign: 'middle', marginRight: 6 }} />
          {group.name} — メンバー管理
        </h3>
        <p style={{ color: t.textMuted, fontSize: '0.875rem', margin: '0 0 1.5rem' }}>
          {members.length} 名
        </p>

        {error && <p style={{ color: t.danger, fontSize: '0.875rem' }}>{error}</p>}

        {loading ? (
          <p style={{ color: t.textMuted }}>読み込み中…</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${t.border}` }}>
                <th style={{ textAlign: 'left', padding: '8px 4px', fontSize: '0.8rem', color: t.textMuted }}>メール</th>
                <th style={{ textAlign: 'left', padding: '8px 4px', fontSize: '0.8rem', color: t.textMuted }}>表示名</th>
                <th style={{ textAlign: 'left', padding: '8px 4px', fontSize: '0.8rem', color: t.textMuted }}>追加日時</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {members.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '1rem', textAlign: 'center', color: t.textMuted }}>
                    メンバーがいません
                  </td>
                </tr>
              ) : (
                members.map(m => (
                  <tr key={m.user_id} style={{ borderBottom: `1px solid ${t.border}` }}>
                    <td style={{ padding: '8px 4px', fontSize: '0.875rem' }}>{m.email}</td>
                    <td style={{ padding: '8px 4px', fontSize: '0.875rem', color: t.textMuted }}>
                      {m.display_name ?? '—'}
                    </td>
                    <td style={{ padding: '8px 4px', fontSize: '0.8rem', color: t.textMuted }}>
                      {new Date(m.added_at).toLocaleDateString('ja-JP')}
                    </td>
                    <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                      <button
                        style={{ ...btnBase, background: 'transparent', color: t.danger, padding: '4px 8px', fontSize: '0.8rem', border: 'none' }}
                        onClick={() => handleRemove(m.user_id)}
                        disabled={saving}
                        title="グループから削除"
                      >
                        <MdPersonRemove />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {addMode ? (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
            <select
              style={{ ...inputStyle, flex: 1 }}
              value={selectedUserId}
              onChange={e => setSelectedUserId(e.target.value)}
            >
              <option value="">ユーザーを選択…</option>
              {addableUsers.map(u => (
                <option key={u.id} value={u.id}>{u.email}</option>
              ))}
            </select>
            <button style={btnPrimary} onClick={handleAdd} disabled={saving || !selectedUserId}>
              追加
            </button>
            <button style={btnGhost} onClick={() => setAddMode(false)}>キャンセル</button>
          </div>
        ) : (
          <button
            style={{ ...btnPrimary, marginBottom: 12 }}
            onClick={() => setAddMode(true)}
            disabled={addableUsers.length === 0}
          >
            <MdPersonAdd /> ユーザーを追加
          </button>
        )}

        <div style={{ textAlign: 'right' }}>
          <button style={btnGhost} onClick={onClose}>閉じる</button>
        </div>
      </div>
    </div>
  )
}

// ─── AdminGroups Page ─────────────────────────────────────────────────────────

export default function AdminGroups() {
  const { user, logout, hasRole, getAccessToken } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isSuperAdmin  = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin       = isSuperAdmin || isTenantAdmin

  const profile     = user?.profile as Record<string, unknown> | undefined
  const email       = (profile?.email as string) ?? ''
  const name        = (profile?.name as string) || (profile?.preferred_username as string) || email
  const initial     = name.charAt(0).toUpperCase() || '?'
  const rawTenantId = profile?.tenant_id
  const tenantName  = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) ?? ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

  // Group list state
  const [groups, setGroups] = useState<Group[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // All users (for member add dropdown)
  const [allUsers, setAllUsers] = useState<EnrichedUser[]>([])

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingGroup, setEditingGroup] = useState<Group | null>(null)
  const [membersGroup, setMembersGroup] = useState<Group | null>(null)

  const PAGE_SIZE = 20

  const fetchGroups = useCallback(async () => {
    const token = getAccessToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await listGroups(token, page, PAGE_SIZE, search || undefined)
      setGroups(res.items)
      setTotal(res.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'グループ取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [getAccessToken, page, search])

  useEffect(() => { fetchGroups() }, [fetchGroups])

  useEffect(() => {
    const token = getAccessToken()
    if (!token) return
    listUsersWithGroups(token).then(setAllUsers).catch(() => {})
  }, [getAccessToken])

  const handleCreate = async (name: string, description: string) => {
    const token = getAccessToken()!
    await createGroup(token, { name, description: description || undefined })
    await fetchGroups()
  }

  const handleEdit = async (name: string, description: string) => {
    if (!editingGroup) return
    const token = getAccessToken()!
    await updateGroup(token, editingGroup.id, { name, description })
    await fetchGroups()
  }

  const handleDelete = async (group: Group) => {
    if (!window.confirm(`グループ「${group.name}」を削除しますか？この操作は取り消せません。`)) return
    const token = getAccessToken()!
    try {
      await deleteGroup(token, group.id)
      await fetchGroups()
    } catch (e) {
      setError(e instanceof Error ? e.message : '削除に失敗しました')
    }
  }

  // ── Layout ─────────────────────────────────────────────────────────────────

  const navItems: NavItem[] = [
    { label: 'ダッシュボード', icon: <MdHome />, path: '/dashboard' },
    ...(isAdmin ? [
      { label: 'ユーザー管理', icon: <MdPeople />, path: '/admin/users' },
      { label: 'グループ管理', icon: <MdGroup />, path: '/admin/groups' },
      { label: '監査ログ', icon: <MdHistory />, path: '/admin/audit' },
      { label: 'セキュリティ設定', icon: <MdLock />, path: '/security' },
    ] : []),
    ...(isSuperAdmin ? [{ label: 'テナント管理', icon: <MdBusiness />, path: '/admin/clients' }] : []),
  ]

  const dropdownItems: DropdownItem[] = [
    { label: '個人セキュリティ設定', icon: <MdManageAccounts />, onClick: () => navigate('/me/security') },
    { label: 'ログアウト', icon: <MdLogout />, onClick: logout, danger: true },
  ]

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div style={{ minHeight: '100vh', background: t.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>

      {/* TopBar */}
      <header style={{
        height: 60, background: t.surface,
        borderBottom: `1px solid ${t.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 16px', position: 'sticky', top: 0, zIndex: 100,
        boxShadow: t.shadowSm,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isMobile && (
            <button
              onClick={() => setDrawerOpen(true)}
              aria-label="メニューを開く"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '8px', borderRadius: t.radiusMd, fontSize: '1.25rem',
                minWidth: 44, minHeight: 44, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >☰</button>
          )}
          <span style={{ fontSize: '1rem', fontWeight: 700, color: t.text }}>{tenantTitle}</span>
        </div>
        <UserDropdown initial={initial} name={name} email={email} items={dropdownItems} />
      </header>

      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navItems}
        currentPath="/admin/groups"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      <div style={{ display: 'flex' }}>
        {!isMobile && (
          <SideNav items={navItems} currentPath="/admin/groups" onNavigate={navigate} />
        )}

        <main style={{ flex: 1, padding: '2rem', maxWidth: 900 }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: t.text }}>グループ管理</h1>
              <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: t.textMuted }}>
                グループの作成・編集・メンバー管理を行います
              </p>
            </div>
            <button style={btnPrimary} onClick={() => setShowCreateModal(true)}>
              <MdAdd /> グループ作成
            </button>
          </div>

          {/* Search */}
          <div style={{ marginBottom: '1rem' }}>
            <input
              style={{ ...inputStyle, maxWidth: 320 }}
              placeholder="グループ名で検索…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
            />
          </div>

          {/* Error */}
          {error && (
            <div style={{
              background: '#fef2f2', border: `1px solid #fca5a5`,
              borderRadius: t.radiusMd, padding: '12px 16px',
              color: t.danger, marginBottom: 16, fontSize: '0.875rem',
            }}>{error}</div>
          )}

          {/* Table */}
          <div style={{ background: t.surface, borderRadius: t.radiusLg, border: `1px solid ${t.border}`, overflow: 'hidden' }}>
            {loading ? (
              <p style={{ padding: '2rem', textAlign: 'center', color: t.textMuted }}>読み込み中…</p>
            ) : groups.length === 0 ? (
              <p style={{ padding: '3rem', textAlign: 'center', color: t.textMuted }}>
                {search ? 'グループが見つかりません' : 'グループがまだありません。「グループ作成」からはじめましょう。'}
              </p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: `1px solid ${t.border}` }}>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>グループ名</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>説明</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>状態</th>
                    <th style={{ padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g, i) => (
                    <tr key={g.id} style={{ borderBottom: i < groups.length - 1 ? `1px solid ${t.border}` : 'none' }}>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: t.text }}>{g.name}</td>
                      <td style={{ padding: '14px 16px', color: t.textMuted, fontSize: '0.875rem' }}>
                        {g.description ?? <span style={{ fontStyle: 'italic' }}>—</span>}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          display: 'inline-block', padding: '2px 10px', borderRadius: 999,
                          fontSize: '0.75rem', fontWeight: 600,
                          background: g.is_active ? '#dcfce7' : '#f1f5f9',
                          color: g.is_active ? '#166534' : '#64748b',
                        }}>
                          {g.is_active ? '有効' : '無効'}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          <button
                            style={{ ...btnGhost, padding: '6px 10px', fontSize: '0.8rem' }}
                            onClick={() => setMembersGroup(g)}
                            title="メンバー管理"
                          >
                            <MdPeople /> メンバー
                          </button>
                          <button
                            style={{ ...btnGhost, padding: '6px 10px', fontSize: '0.8rem' }}
                            onClick={() => setEditingGroup(g)}
                            title="編集"
                          >
                            <MdEdit />
                          </button>
                          <button
                            style={{ ...btnBase, background: 'transparent', color: t.danger, border: `1px solid #fca5a5`, padding: '6px 10px', fontSize: '0.8rem' }}
                            onClick={() => handleDelete(g)}
                            title="削除"
                          >
                            <MdDelete />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 16, justifyContent: 'center' }}>
              <button style={btnGhost} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>←</button>
              <span style={{ fontSize: '0.875rem', color: t.textMuted }}>{page} / {totalPages}</span>
              <button style={btnGhost} disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</button>
            </div>
          )}
        </main>
      </div>

      {/* Modals */}
      {showCreateModal && (
        <GroupFormModal
          onSave={handleCreate}
          onClose={() => setShowCreateModal(false)}
        />
      )}
      {editingGroup && (
        <GroupFormModal
          group={editingGroup}
          onSave={handleEdit}
          onClose={() => setEditingGroup(null)}
        />
      )}
      {membersGroup && (
        <MembersModal
          group={membersGroup}
          token={getAccessToken()!}
          allUsers={allUsers}
          onClose={() => setMembersGroup(null)}
        />
      )}
    </div>
  )
}
