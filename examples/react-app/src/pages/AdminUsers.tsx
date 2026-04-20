import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type AdminUser,
  type EnrichedUser,
  type CreateUserInput,
  type UpdateUserInput,
  type InvitationBulkResponse,
  listUsers,
  listUsersWithGroups,
  createUser,
  createInvitations,
  getUser,
  updateUser,
  disableUser,
  resetPassword,
  resetMfa,
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
  MdHome, MdPeople, MdLock, MdBusiness, MdManageAccounts, MdLogout, MdSecurity,
  MdGroup, MdHistory,
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
  width: '100%', maxWidth: 480,
  boxShadow: t.shadowMd,
}
const mfaModalBox: React.CSSProperties = {
  background: t.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 400,
  boxShadow: t.shadowMd,
}
const inviteModalBox: React.CSSProperties = {
  background: t.surface, borderRadius: 12, padding: '2rem',
  width: '100%', maxWidth: 560,
  boxShadow: t.shadowMd,
}

// ─── Merged User Type (Keycloak + App DB) ─────────────────────────────────────

interface MergedUser {
  id: string
  email: string
  displayName: string
  enabled: boolean
  groups: string[]
  firstName?: string
  lastName?: string
  username?: string
}

// ─── Sort / Filter types ──────────────────────────────────────────────────────

type SortKey = 'name' | 'email' | 'groups' | 'status'
type SortDir = 'asc' | 'desc'

// ─── Badge colors for groups ──────────────────────────────────────────────────

const BADGE_COLORS = [
  { bg: '#dbeafe', fg: '#1e40af' },
  { bg: '#dcfce7', fg: '#166534' },
  { bg: '#fef3c7', fg: '#92400e' },
  { bg: '#fce7f3', fg: '#9d174d' },
  { bg: '#e0e7ff', fg: '#3730a3' },
  { bg: '#f1f5f9', fg: '#475569' },
]

function badgeColor(name: string) {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0
  return BADGE_COLORS[Math.abs(h) % BADGE_COLORS.length]
}

// ─── GroupBadges Component ────────────────────────────────────────────────────

const MAX_VISIBLE_BADGES = 2

function GroupBadges({ groups }: { groups: string[] }) {
  const [showTooltip, setShowTooltip] = useState(false)

  if (groups.length === 0) {
    return (
      <span style={{ fontSize: '0.75rem', color: t.textMuted, fontStyle: 'italic' }}>
        未所属
      </span>
    )
  }

  const visible = groups.slice(0, MAX_VISIBLE_BADGES)
  const remaining = groups.slice(MAX_VISIBLE_BADGES)

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
      {visible.map((g) => {
        const c = badgeColor(g)
        return (
          <span
            key={g}
            style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: 12,
              fontSize: '0.7rem', fontWeight: 500, whiteSpace: 'nowrap',
              background: c.bg, color: c.fg,
            }}
          >
            {g}
          </span>
        )
      })}
      {remaining.length > 0 && (
        <div
          style={{ position: 'relative', display: 'inline-block' }}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <span
            style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: 12,
              fontSize: '0.7rem', fontWeight: 600, whiteSpace: 'nowrap',
              background: '#f1f5f9', color: '#475569', cursor: 'default',
            }}
          >
            +{remaining.length}
          </span>
          {showTooltip && (
            <div
              style={{
                position: 'absolute', bottom: 'calc(100% + 6px)', left: '50%',
                transform: 'translateX(-50%)',
                background: '#1e293b', color: '#fff', borderRadius: 6,
                padding: '6px 10px', fontSize: '0.72rem', lineHeight: 1.6,
                whiteSpace: 'nowrap', zIndex: 50,
                boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
              }}
            >
              {remaining.map((g) => (
                <div key={g}>{g}</div>
              ))}
              {/* Arrow */}
              <div
                style={{
                  position: 'absolute', top: '100%', left: '50%',
                  transform: 'translateX(-50%)',
                  width: 0, height: 0,
                  borderLeft: '5px solid transparent',
                  borderRight: '5px solid transparent',
                  borderTop: '5px solid #1e293b',
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Form Types ───────────────────────────────────────────────────────────────

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
  const [searchParams, setSearchParams] = useSearchParams()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isSuperAdmin  = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin       = isSuperAdmin || isTenantAdmin
  const profile       = user?.profile as Record<string, unknown> | undefined
  const adminEmail    = profile?.email as string | undefined ?? ''
  const adminName     = (profile?.name as string)
                     || (profile?.preferred_username as string)
                     || adminEmail
  const adminInitial  = adminName.charAt(0).toUpperCase() || '?'

  const rawTenantId = profile?.tenant_id
  const tenantName  = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) ?? ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

  // ── Data state ──────────────────────────────────────────────────────────
  const [users, setUsers] = useState<MergedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  // ── Sort / Filter state ─────────────────────────────────────────────────
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [filterGroup, setFilterGroup] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  // ── Modal state ─────────────────────────────────────────────────────────
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate())
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmailsText, setInviteEmailsText] = useState('')
  const [inviteRole, setInviteRole] = useState<'user' | 'tenant_admin'>('user')
  const [inviteCustomMessage, setInviteCustomMessage] = useState('')
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteResult, setInviteResult] = useState<InvitationBulkResponse | null>(null)
  const [inviting, setInviting] = useState(false)

  const [editTarget, setEditTarget] = useState<AdminUser | null>(null)
  const [editForm, setEditForm] = useState<EditForm | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [mfaTarget,  setMfaTarget]  = useState<MergedUser | null>(null)
  const [mfaLoading, setMfaLoading] = useState(false)
  const [openActionMenuUserId, setOpenActionMenuUserId] = useState<string | null>(null)

  const loaded = useRef(false)

  // ── fetch (merge Keycloak + App DB) ────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    const token = getAccessToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const kcUsers = await listUsers(token)

      // Try fetching enriched data from App DB (may be unavailable)
      let dbUsers: EnrichedUser[] = []
      try {
        dbUsers = await listUsersWithGroups(token)
      } catch {
        // App DB endpoint not available — fall back to Keycloak-only
      }

      const dbMap = new Map(dbUsers.map((u) => [u.id, u]))
      const merged: MergedUser[] = []
      const seen = new Set<string>()

      // Keycloak users enriched with DB groups
      for (const kc of kcUsers) {
        const db = dbMap.get(kc.id)
        merged.push({
          id: kc.id,
          email: kc.email,
          displayName:
            db?.displayName ||
            [kc.firstName, kc.lastName].filter(Boolean).join(' ') ||
            kc.username ||
            kc.email,
          enabled: kc.enabled,
          groups: db?.groups ?? [],
          firstName: kc.firstName,
          lastName: kc.lastName,
          username: kc.username,
        })
        seen.add(kc.id)
      }

      // DB-only users (not yet in Keycloak)
      for (const db of dbUsers) {
        if (!seen.has(db.id)) {
          merged.push({
            id: db.id,
            email: db.email,
            displayName: db.displayName || db.email,
            enabled: db.enabled,
            groups: db.groups,
          })
        }
      }

      setUsers(merged)
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

  useEffect(() => {
    const close = () => setOpenActionMenuUserId(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  // ── Derived: available groups for filter ────────────────────────────────
  const allGroups = useMemo(() => {
    const set = new Set<string>()
    users.forEach((u) => u.groups.forEach((g) => set.add(g)))
    return [...set].sort((a, b) => a.localeCompare(b, 'ja'))
  }, [users])

  // ── Derived: filtered + sorted list ─────────────────────────────────────
  const processed = useMemo(() => {
    const q = search.toLowerCase()
    let result = users.filter((u) => {
      const matchSearch =
        !q ||
        u.email.toLowerCase().includes(q) ||
        u.displayName.toLowerCase().includes(q)
      const matchGroup =
        !filterGroup ||
        (filterGroup === '__none__'
          ? u.groups.length === 0
          : u.groups.includes(filterGroup))
      const matchStatus =
        !filterStatus ||
        (filterStatus === 'active' ? u.enabled : !u.enabled)
      return matchSearch && matchGroup && matchStatus
    })

    result = [...result].sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'name':
          cmp = a.displayName.localeCompare(b.displayName, 'ja')
          break
        case 'email':
          cmp = a.email.localeCompare(b.email)
          break
        case 'groups':
          cmp = (a.groups[0] ?? '').localeCompare(b.groups[0] ?? '', 'ja')
          break
        case 'status':
          cmp = a.enabled === b.enabled ? 0 : a.enabled ? -1 : 1
          break
      }
      return sortDir === 'desc' ? -cmp : cmp
    })

    return result
  }, [users, search, filterGroup, filterStatus, sortKey, sortDir])

  // ── Sort toggle ─────────────────────────────────────────────────────────
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  // ── create ─────────────────────────────────────────────────────────────
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

  const inviteEmails = useMemo(() => {
    return inviteEmailsText
      .split(/[\n,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0)
  }, [inviteEmailsText])

  const openInviteModal = () => {
    setInviteError(null)
    setInviteResult(null)
    setInviteEmailsText('')
    setInviteRole('user')
    setInviteCustomMessage('')
    setShowInvite(true)
  }

  useEffect(() => {
    if (searchParams.get('invite') !== '1') return
    openInviteModal()
    const next = new URLSearchParams(searchParams)
    next.delete('invite')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const handleInviteSubmit = async () => {
    const token = getAccessToken()
    if (!token) return
    if (inviteEmails.length === 0) {
      setInviteError('メールアドレスを1件以上入力してください')
      return
    }
    if (inviteEmails.length > 50) {
      setInviteError('一度に招待できるのは50件までです')
      return
    }

    setInviting(true)
    setInviteError(null)
    setInviteResult(null)
    try {
      const res = await createInvitations(token, {
        invitations: inviteEmails.map((email) => ({ email, role: inviteRole })),
        custom_message: inviteCustomMessage.trim() || undefined,
      })
      setInviteResult(res)

      if (res.failed.length === 0) {
        setShowInvite(false)
      }
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : '招待の送信に失敗しました')
    } finally {
      setInviting(false)
    }
  }

  // ── edit (fetches fresh Keycloak data for the form) ────────────────────
  const openEdit = async (u: MergedUser) => {
    const token = getAccessToken()
    if (!token) return
    setEditError(null)
    try {
      const kcUser = await getUser(token, u.id)
      setEditTarget(kcUser)
      setEditForm(toEditForm(kcUser))
    } catch {
      setEditTarget({
        id: u.id, email: u.email, username: u.email, enabled: u.enabled,
        emailVerified: true, firstName: u.displayName.split(' ')[0],
        lastName: u.displayName.split(' ').slice(1).join(' '),
      })
      setEditForm({
        firstName: u.displayName.split(' ')[0] ?? '',
        lastName: u.displayName.split(' ').slice(1).join(' ') ?? '',
        email: u.email, newPassword: '', resetPassword: false,
      })
    }
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

  // ── MFA reset ──────────────────────────────────────────────────────────
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

  // ── toggle enabled ─────────────────────────────────────────────────────
  const toggleEnabled = async (u: MergedUser) => {
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

  // ─── Sortable header helper ─────────────────────────────────────────────
  const thStyle: React.CSSProperties = {
    padding: '10px 16px', textAlign: 'left', fontSize: '0.75rem',
    fontWeight: 600, color: t.textMuted, textTransform: 'uppercase',
    letterSpacing: '0.05em', borderBottom: `1px solid ${t.border}`,
    cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap',
  }
  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''

  // ─── render ────────────────────────────────────────────────────────────────
  const navItems: NavItem[] = [
    { label: 'ダッシュボード', icon: <MdHome />, path: '/dashboard' },
    ...(isAdmin      ? [
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

  return (
    <div style={{ minHeight: '100vh', background: t.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>

      {/* ── TopBar ── */}
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
              aria-expanded={drawerOpen}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '8px', borderRadius: t.radiusMd,
                fontSize: '1.25rem', minWidth: 44, minHeight: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              ☰
            </button>
          )}
          <span style={{ fontSize: '1rem', fontWeight: 700, color: t.text }}>{tenantTitle}</span>
        </div>

        <UserDropdown
          initial={adminInitial}
          name={adminName}
          email={adminEmail}
          items={dropdownItems}
        />
      </header>

      {/* ── Mobile Drawer ── */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navItems}
        currentPath="/admin/users"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      {/* ── Body ── */}
      <div style={{ display: 'flex' }}>

        {/* PC SideNav */}
        {!isMobile && (
          <SideNav
            items={navItems}
            currentPath="/admin/users"
            onNavigate={navigate}
          />
        )}

        {/* Main */}
        <main style={{ flex: 1, minWidth: 0, padding: isMobile ? '16px' : '24px' }}>

          {/* Page header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '20px', flexWrap: 'wrap' }}>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: t.text, flex: 1 }}>
              <MdPeople style={{ verticalAlign: 'middle', marginRight: 6 }} /> ユーザー管理
              {isSuperAdmin && (
                <span style={{ fontSize: '0.875rem', fontWeight: 400, color: t.textMuted, marginLeft: '0.5rem' }}>
                  — 全テナント
                </span>
              )}
            </h1>
            <button
              onClick={openInviteModal}
              style={{
                padding: '8px 16px', borderRadius: t.radiusMd,
                background: t.primary, color: t.textInverse,
                border: 'none', cursor: 'pointer',
                fontSize: '0.875rem', fontWeight: 600,
              }}
            >
              + ユーザーを招待
            </button>
          </div>

          {/* Search + Filters */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="名前・メールで検索..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                flex: '1 1 200px', padding: '8px 12px',
                border: `1px solid ${t.border}`, borderRadius: t.radiusMd,
                fontSize: '0.9rem', boxSizing: 'border-box', outline: 'none',
              }}
            />
            <select
              value={filterGroup}
              onChange={(e) => setFilterGroup(e.target.value)}
              style={{
                padding: '8px 12px', border: `1px solid ${t.border}`,
                borderRadius: t.radiusMd, fontSize: '0.85rem',
                background: t.surface, color: t.text, outline: 'none',
              }}
            >
              <option value="">全グループ</option>
              {allGroups.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
              <option value="__none__">未所属</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{
                padding: '8px 12px', border: `1px solid ${t.border}`,
                borderRadius: t.radiusMd, fontSize: '0.85rem',
                background: t.surface, color: t.text, outline: 'none',
              }}
            >
              <option value="">全ステータス</option>
              <option value="active">有効</option>
              <option value="inactive">無効</option>
            </select>
          </div>

          {/* Table */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: t.textMuted }}>読み込み中...</div>
          ) : error ? (
            <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '1rem', borderRadius: t.radiusMd, display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <strong>エラー:</strong> {error}
              <button onClick={fetchUsers} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #b91c1c', background: 'none', color: '#b91c1c', cursor: 'pointer', fontSize: '0.8rem' }}>
                再試行
              </button>
            </div>
          ) : (
            <div style={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: t.radiusLg, boxShadow: t.shadowSm }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: t.bg }}>
                    <th style={thStyle} onClick={() => toggleSort('name')}>
                      ユーザー{sortIndicator('name')}
                    </th>
                    <th style={thStyle} onClick={() => toggleSort('email')}>
                      メール{sortIndicator('email')}
                    </th>
                    <th style={thStyle} onClick={() => toggleSort('groups')}>
                      グループ{sortIndicator('groups')}
                    </th>
                    <th style={thStyle} onClick={() => toggleSort('status')}>
                      ステータス{sortIndicator('status')}
                    </th>
                    <th style={{ ...thStyle, cursor: 'default' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {processed.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: t.textMuted }}>ユーザーが見つかりません</td></tr>
                  ) : processed.map((u, idx) => {
                    const initial = u.displayName.charAt(0).toUpperCase()
                    return (
                      <tr key={u.id} style={{ borderBottom: idx < processed.length - 1 ? `1px solid ${t.border}` : 'none' }}>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ width: 36, height: 36, borderRadius: t.radiusFull, background: t.primary, color: t.textInverse, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem', flexShrink: 0 }}>
                              {initial}
                            </div>
                            <span style={{ fontWeight: 500, fontSize: '0.9rem', color: t.text }}>{u.displayName}</span>
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px', color: t.textMuted, fontSize: '0.875rem' }}>{u.email}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <GroupBadges groups={u.groups} />
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-block', padding: '3px 10px', borderRadius: t.radiusFull,
                            fontSize: '0.75rem', fontWeight: 600,
                            background: u.enabled ? '#dcfce7' : '#fee2e2',
                            color:      u.enabled ? '#15803d' : '#b91c1c',
                          }}>
                            {u.enabled ? '有効' : '無効'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ position: 'relative', display: 'inline-block' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setOpenActionMenuUserId((current) => current === u.id ? null : u.id)
                              }}
                              style={{
                                padding: '6px 10px', borderRadius: t.radiusMd,
                                border: `1px solid ${t.border}`, background: t.surface,
                                cursor: 'pointer', fontSize: '0.8rem', color: t.text,
                              }}
                              aria-haspopup="menu"
                              aria-expanded={openActionMenuUserId === u.id}
                            >
                              操作 ▾
                            </button>

                            {openActionMenuUserId === u.id && (
                              <div
                                role="menu"
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                  position: 'absolute', right: 0, top: 'calc(100% + 6px)',
                                  minWidth: 170, background: t.surface,
                                  border: `1px solid ${t.border}`, borderRadius: t.radiusMd,
                                  boxShadow: t.shadowSm, zIndex: 30, overflow: 'hidden',
                                }}
                              >
                                <button
                                  role="menuitem"
                                  onClick={() => {
                                    setOpenActionMenuUserId(null)
                                    openEdit(u)
                                  }}
                                  style={{
                                    width: '100%', padding: '10px 12px', border: 'none',
                                    background: t.surface, color: t.text, textAlign: 'left', cursor: 'pointer',
                                  }}
                                >
                                  編集
                                </button>
                                <button
                                  role="menuitem"
                                  onClick={() => {
                                    setOpenActionMenuUserId(null)
                                    toggleEnabled(u)
                                  }}
                                  style={{
                                    width: '100%', padding: '10px 12px', border: 'none',
                                    background: t.surface, color: u.enabled ? t.danger : t.primary, textAlign: 'left', cursor: 'pointer',
                                  }}
                                >
                                  {u.enabled ? '無効化' : '有効化'}
                                </button>
                                <button
                                  role="menuitem"
                                  onClick={() => {
                                    setOpenActionMenuUserId(null)
                                    setMfaTarget(u)
                                  }}
                                  style={{
                                    width: '100%', padding: '10px 12px', border: 'none',
                                    background: t.surface, color: t.text, textAlign: 'left', cursor: 'pointer',
                                  }}
                                >
                                  MFAリセット
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div style={{ padding: '8px 16px', borderTop: `1px solid ${t.border}`, fontSize: '0.78rem', color: t.textMuted }}>
                {processed.length} 件 / 全 {users.length} 件
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
              <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}><MdSecurity /></div>
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem' }}>MFA 設定をリセット</h2>
              <p style={{ margin: 0, color: t.textMuted, fontSize: '0.875rem', lineHeight: 1.6 }}>
                <strong>{mfaTarget.displayName || mfaTarget.email}</strong> の
                MFA（二要素認証）設定を削除します。<br />
                次回ログイン時にMFAを再設定するよう求められます。
              </p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setMfaTarget(null)} disabled={mfaLoading}
                style={{ padding: '8px 16px', borderRadius: t.radiusMd, background: 'none', border: `1px solid ${t.border}`, fontSize: '0.875rem', cursor: mfaLoading ? 'not-allowed' : 'pointer', color: t.text, opacity: mfaLoading ? 0.5 : 1 }}>
                キャンセル
              </button>
              <button onClick={handleMfaReset} disabled={mfaLoading}
                style={{ padding: '8px 20px', borderRadius: t.radiusMd, background: '#f59e0b', color: t.textInverse, border: 'none', cursor: mfaLoading ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: mfaLoading ? 0.6 : 1 }}>
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
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>メールアドレス <span style={{ color: t.danger }}>*</span></span>
                <input type="email" value={createForm.email} onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="user@example.com"
                  style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
              </label>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>姓</span>
                  <input type="text" value={createForm.lastName} onChange={(e) => setCreateForm((f) => ({ ...f, lastName: e.target.value }))}
                    placeholder="山田"
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                </label>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>名</span>
                  <input type="text" value={createForm.firstName} onChange={(e) => setCreateForm((f) => ({ ...f, firstName: e.target.value }))}
                    placeholder="太郎"
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                </label>
              </div>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>初期パスワード <span style={{ color: t.danger }}>*</span></span>
                <input type="password" value={createForm.password} onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  placeholder="8文字以上"
                  style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={createForm.temporary} onChange={(e) => setCreateForm((f) => ({ ...f, temporary: e.target.checked }))} />
                <span style={{ fontSize: '0.875rem' }}>一時パスワード（初回ログイン時に変更を要求）</span>
              </label>
              {createError && <div style={{ color: t.danger, fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>{createError}</div>}
            </div>
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setShowCreate(false)} disabled={creating}
                style={{ padding: '8px 16px', borderRadius: t.radiusMd, background: 'none', border: `1px solid ${t.border}`, fontSize: '0.875rem', cursor: creating ? 'not-allowed' : 'pointer', color: t.text, opacity: creating ? 0.5 : 1 }}>キャンセル</button>
              <button onClick={handleCreate} disabled={creating}
                style={{ padding: '8px 20px', borderRadius: t.radiusMd, background: t.primary, color: t.textInverse, border: 'none', cursor: creating ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: creating ? 0.6 : 1 }}>
                {creating ? '作成中...' : '追加する'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Invite Modal ──────────────────────────────────────────────────── */}
      {showInvite && (
        <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget && !inviting) setShowInvite(false) }}>
          <div style={inviteModalBox}>
            <h2 style={{ margin: '0 0 1rem 0' }}>ユーザー招待</h2>
            <p style={{ margin: '0 0 1rem 0', color: t.textMuted, fontSize: '0.875rem' }}>
              メールアドレスをカンマまたは改行で区切って入力してください（最大50件）。
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                  メールアドレス <span style={{ color: t.danger }}>*</span>
                </span>
                <textarea
                  value={inviteEmailsText}
                  onChange={(e) => setInviteEmailsText(e.target.value)}
                  rows={4}
                  placeholder={'user1@example.com\nuser2@example.com'}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    border: `1px solid ${t.border}`,
                    borderRadius: 8,
                    fontSize: '0.95rem',
                    boxSizing: 'border-box',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
                <span style={{ fontSize: '0.8rem', color: t.textMuted }}>{inviteEmails.length} 件</span>
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>権限</span>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'user' | 'tenant_admin')}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    border: `1px solid ${t.border}`,
                    borderRadius: 8,
                    fontSize: '0.95rem',
                    boxSizing: 'border-box',
                    background: t.surface,
                    color: t.text,
                  }}
                >
                  <option value="user">一般ユーザー</option>
                  <option value="tenant_admin">テナント管理者</option>
                </select>
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>メッセージ（任意）</span>
                <textarea
                  value={inviteCustomMessage}
                  onChange={(e) => setInviteCustomMessage(e.target.value)}
                  rows={3}
                  maxLength={500}
                  placeholder="招待メールに添えるメッセージ"
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    border: `1px solid ${t.border}`,
                    borderRadius: 8,
                    fontSize: '0.95rem',
                    boxSizing: 'border-box',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
              </label>

              {inviteError && (
                <div style={{ color: t.danger, fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>
                  {inviteError}
                </div>
              )}

              {inviteResult && (
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  <div style={{ color: '#166534', fontSize: '0.875rem', background: '#dcfce7', padding: '0.5rem 0.75rem', borderRadius: 6 }}>
                    送信成功: {inviteResult.succeeded.length}件
                  </div>
                  {inviteResult.failed.length > 0 && (
                    <div style={{ color: '#991b1b', fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>
                      送信失敗: {inviteResult.failed.length}件
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ marginTop: '1.2rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setShowInvite(false)}
                disabled={inviting}
                style={{
                  padding: '8px 16px', borderRadius: t.radiusMd,
                  background: 'none', border: `1px solid ${t.border}`,
                  fontSize: '0.875rem', cursor: inviting ? 'not-allowed' : 'pointer',
                  color: t.text, opacity: inviting ? 0.5 : 1,
                }}
              >
                キャンセル
              </button>
              <button
                onClick={handleInviteSubmit}
                disabled={inviting || inviteEmails.length === 0}
                style={{
                  padding: '8px 20px', borderRadius: t.radiusMd,
                  background: t.primary, color: t.textInverse, border: 'none',
                  cursor: inviting || inviteEmails.length === 0 ? 'not-allowed' : 'pointer',
                  fontSize: '0.875rem', fontWeight: 600,
                  opacity: inviting || inviteEmails.length === 0 ? 0.6 : 1,
                }}
              >
                {inviting ? '送信中...' : `招待を送信 (${inviteEmails.length}件)`}
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
                  style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
              </label>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>姓</span>
                  <input type="text" value={editForm.lastName} onChange={(e) => setEditForm((f) => f && ({ ...f, lastName: e.target.value }))}
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                </label>
                <label style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>名</span>
                  <input type="text" value={editForm.firstName} onChange={(e) => setEditForm((f) => f && ({ ...f, firstName: e.target.value }))}
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                </label>
              </div>
              <div style={{ borderTop: `1px solid ${t.border}`, paddingTop: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.75rem' }}>
                  <input type="checkbox" checked={editForm.resetPassword} onChange={(e) => setEditForm((f) => f && ({ ...f, resetPassword: e.target.checked }))} />
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>パスワードをリセットする</span>
                </label>
                {editForm.resetPassword && (
                  <input type="password" value={editForm.newPassword} onChange={(e) => setEditForm((f) => f && ({ ...f, newPassword: e.target.value }))}
                    placeholder="新しいパスワード"
                    style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${t.border}`, borderRadius: 8, fontSize: '1rem', boxSizing: 'border-box' }} />
                )}
              </div>
              {editError && <div style={{ color: t.danger, fontSize: '0.875rem', background: '#fee2e2', padding: '0.5rem 0.75rem', borderRadius: 6 }}>{editError}</div>}
            </div>
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button onClick={() => setEditTarget(null)} disabled={saving}
                style={{ padding: '8px 16px', borderRadius: t.radiusMd, background: 'none', border: `1px solid ${t.border}`, fontSize: '0.875rem', cursor: saving ? 'not-allowed' : 'pointer', color: t.text, opacity: saving ? 0.5 : 1 }}>キャンセル</button>
              <button onClick={handleSave} disabled={saving}
                style={{ padding: '8px 20px', borderRadius: t.radiusMd, background: t.primary, color: t.textInverse, border: 'none', cursor: saving ? 'not-allowed' : 'pointer', fontSize: '0.875rem', fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
                {saving ? '保存中...' : '保存する'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
