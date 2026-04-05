/**
 * AdminInvitations ページ (/admin/invitations)
 *
 * テナント内の招待一覧を表示・管理する。
 * 権限: tenant_admin / super_admin のみ（AuthGuard で保護）
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type InvitationResponse,
  listInvitations,
  revokeInvitation,
  resendInvitation,
} from '../api/adminApi'
import { t } from '../theme/tokens'
import { useIsMobile, UserDropdown, SideNav, MobileDrawer, type NavItem, type DropdownItem } from '../components/layout'

// ─── Nav helpers ──────────────────────────────────────────────────────────────

function buildNavItems(hasAdminRole: boolean): NavItem[] {
  const items: NavItem[] = [{ label: 'ダッシュボード', icon: '🏠', path: '/dashboard' }]
  if (hasAdminRole) {
    items.push(
      { label: 'ユーザー管理', icon: '👥', path: '/admin/users' },
      { label: '招待管理', icon: '📨', path: '/admin/invitations' },
      { label: 'セキュリティ設定', icon: '🔒', path: '/security' },
    )
  }
  return items
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

type EffectiveStatus = 'pending' | 'accepted' | 'expired' | 'revoked'

const STATUS_CONFIG: Record<
  EffectiveStatus,
  { icon: string; label: string; bg: string; fg: string }
> = {
  pending:  { icon: '⏳', label: '招待中', bg: '#eff6ff', fg: '#1d4ed8' },
  accepted: { icon: '✅', label: '承認済', bg: '#f0fdf4', fg: '#166534' },
  expired:  { icon: '⌛', label: '期限切れ', bg: '#fafafa', fg: '#64748b' },
  revoked:  { icon: '🚫', label: '取消済', bg: '#fef2f2', fg: '#991b1b' },
}

function StatusBadge({ status }: { status: EffectiveStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.revoked
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 10px',
        borderRadius: t.radiusFull,
        fontSize: '0.75rem',
        fontWeight: 600,
        background: cfg.bg,
        color: cfg.fg,
        whiteSpace: 'nowrap',
      }}
    >
      {cfg.icon} {cfg.label}
    </span>
  )
}

// ─── Expiry countdown ─────────────────────────────────────────────────────────

function ExpiryCell({ expiresAt, status }: { expiresAt: string; status: EffectiveStatus }) {
  if (status !== 'pending') return <span style={{ color: t.textMuted }}>—</span>
  const diffMs = new Date(expiresAt).getTime() - Date.now()
  if (diffMs <= 0) return <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>期限切れ</span>
  const hours = Math.floor(diffMs / 3_600_000)
  const days = Math.floor(hours / 24)
  if (days >= 1) return <span style={{ fontSize: '0.85rem', color: t.textMuted }}>{days}日後</span>
  return <span style={{ fontSize: '0.85rem', color: '#d97706' }}>{hours}時間後</span>
}

// ─── Role label ───────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const isAdmin = role === 'tenant_admin'
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: t.radiusFull,
        fontSize: '0.75rem',
        fontWeight: 600,
        background: isAdmin ? '#fef3c7' : '#f1f5f9',
        color: isAdmin ? '#92400e' : '#475569',
      }}
    >
      {isAdmin ? '管理者' : 'ユーザー'}
    </span>
  )
}

// ─── Confirm modal ────────────────────────────────────────────────────────────

function ConfirmModal({
  message,
  onConfirm,
  onCancel,
}: {
  message: string
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: t.surface,
          borderRadius: t.radiusLg,
          padding: '2rem',
          width: '100%',
          maxWidth: 400,
          boxShadow: t.shadowMd,
        }}
      >
        <p style={{ color: t.text, marginTop: 0, lineHeight: 1.6 }}>{message}</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '8px 20px',
              border: `1.5px solid ${t.border}`,
              borderRadius: t.radiusMd,
              background: t.surface,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
            }}
          >
            キャンセル
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: '8px 20px',
              border: 'none',
              borderRadius: t.radiusMd,
              background: t.danger,
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
            }}
          >
            実行する
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Filter tabs ──────────────────────────────────────────────────────────────

type FilterStatus = 'all' | EffectiveStatus

const FILTER_LABELS: Record<FilterStatus, string> = {
  all: 'すべて',
  pending: '招待中',
  accepted: '承認済',
  expired: '期限切れ',
  revoked: '取消済',
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AdminInvitations() {
  const { user, getAccessToken, logout } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const [invitations, setInvitations] = useState<InvitationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Confirm modal state
  const [confirmModal, setConfirmModal] = useState<{
    message: string
    onConfirm: () => void
  } | null>(null)

  const hasAdminRole = useMemo(() => {
    const roles: string[] = (user as any)?.roles ?? []
    return roles.includes('tenant_admin') || roles.includes('super_admin')
  }, [user])

  // Load invitations
  const load = useCallback(async () => {
    setLoading(true)
    setActionError(null)
    try {
      const token = getAccessToken()
      if (!token) return
      const data = await listInvitations(token, filter === 'all' ? undefined : filter)
      setInvitations(data)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '招待一覧の取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [filter, getAccessToken])

  useEffect(() => {
    load()
  }, [load])

  // Revoke
  const handleRevoke = useCallback(
    (inv: InvitationResponse) => {
      setConfirmModal({
        message: `${inv.email} への招待を取り消しますか？`,
        onConfirm: async () => {
          setConfirmModal(null)
          setActionLoading(inv.id)
          setActionError(null)
          try {
            const token = getAccessToken()
            if (!token) return
            await revokeInvitation(token, inv.id)
            setInvitations((prev) =>
              prev.map((i) =>
                i.id === inv.id ? { ...i, status: 'revoked', effective_status: 'revoked' } : i,
              ),
            )
          } catch (err) {
            setActionError(err instanceof Error ? err.message : '取り消しに失敗しました')
          } finally {
            setActionLoading(null)
          }
        },
      })
    },
    [getAccessToken],
  )

  // Resend
  const handleResend = useCallback(
    async (inv: InvitationResponse) => {
      setActionLoading(inv.id)
      setActionError(null)
      try {
        const token = getAccessToken()
        if (!token) return
        const updated = await resendInvitation(token, inv.id)
        // 再送では新しい招待が返る（旧 id は revoked になり新 id が作成される）
        await load()
        void updated
      } catch (err) {
        setActionError(err instanceof Error ? err.message : '再送に失敗しました')
      } finally {
        setActionLoading(null)
      }
    },
    [getAccessToken, load],
  )

  const [drawerOpen, setDrawerOpen] = useState(false)
  const displayName = (user as any)?.displayName ?? (user as any)?.email ?? 'ユーザー'
  const initial = displayName.charAt(0).toUpperCase()
  const dropdownItems: DropdownItem[] = [
    { label: 'ダッシュボード', icon: '🏠', onClick: () => navigate('/dashboard') },
    { label: 'セキュリティ設定', icon: '🔐', onClick: () => navigate('/me/security') },
    { label: 'ログアウト', icon: '🚪', onClick: () => logout(), danger: true },
  ]
  const navList = buildNavItems(hasAdminRole)

  return (
    <div style={{ minHeight: '100vh', background: t.bg, display: 'flex', flexDirection: 'column' }}>
      {/* Confirm modal */}
      {confirmModal && (
        <ConfirmModal
          message={confirmModal.message}
          onConfirm={confirmModal.onConfirm}
          onCancel={() => setConfirmModal(null)}
        />
      )}

      {/* Header */}
      <header
        style={{
          background: t.surface,
          borderBottom: `1px solid ${t.border}`,
          padding: '0 1.5rem',
          height: 60,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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
          <div style={{ fontWeight: 700, fontSize: '1.1rem', color: t.primary }}>
            Common Auth
          </div>
        </div>
        <UserDropdown
          initial={initial}
          name={displayName}
          email={(user as any)?.email ?? ''}
          items={dropdownItems}
        />
      </header>

      {/* Mobile Drawer */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navList}
        currentPath="/admin/invitations"
        onNavigate={navigate}
        tenantTitle="Common Auth"
      />

      <div style={{ display: 'flex', flex: 1 }}>
        {/* SideNav (desktop) */}
        {!isMobile && (
          <SideNav
            items={navList}
            currentPath="/admin/invitations"
            onNavigate={navigate}
          />
        )}

        {/* Main content */}
        <main style={{ flex: 1, padding: isMobile ? '1rem' : '2rem', overflowX: 'auto' }}>
          {/* Page header row */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.5rem',
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: t.text, margin: 0 }}>
              招待管理
            </h1>
            <button
              onClick={() => navigate('/admin/users?invite=1')}
              style={{
                padding: '10px 20px',
                background: t.primary,
                color: '#fff',
                border: 'none',
                borderRadius: t.radiusMd,
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: 'pointer',
              }}
            >
              + 招待を送る
            </button>
          </div>

          {/* Error banner */}
          {actionError && (
            <div
              style={{
                background: '#fef2f2',
                border: `1px solid #fecaca`,
                borderRadius: t.radiusMd,
                padding: '0.75rem 1rem',
                color: t.danger,
                marginBottom: '1rem',
                fontSize: '0.9rem',
              }}
            >
              {actionError}
            </div>
          )}

          {/* Filter tabs */}
          <div
            style={{
              display: 'flex',
              gap: 8,
              marginBottom: '1rem',
              flexWrap: 'wrap',
            }}
          >
            {(Object.keys(FILTER_LABELS) as FilterStatus[]).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                style={{
                  padding: '6px 14px',
                  borderRadius: t.radiusFull,
                  border: filter === s ? `2px solid ${t.primary}` : `1.5px solid ${t.border}`,
                  background: filter === s ? '#eff6ff' : t.surface,
                  color: filter === s ? t.primary : t.textMuted,
                  fontWeight: filter === s ? 700 : 500,
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                }}
              >
                {FILTER_LABELS[s]}
              </button>
            ))}
            <button
              onClick={load}
              style={{
                marginLeft: 'auto',
                padding: '6px 14px',
                borderRadius: t.radiusFull,
                border: `1.5px solid ${t.border}`,
                background: t.surface,
                color: t.textMuted,
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              🔄 更新
            </button>
          </div>

          {/* Table */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '4rem', color: t.textMuted }}>
              読み込み中...
            </div>
          ) : invitations.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '4rem',
                background: t.surface,
                borderRadius: t.radiusLg,
                border: `1px solid ${t.border}`,
                color: t.textMuted,
              }}
            >
              <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>📭</div>
              <p>招待はありません</p>
              <button
                onClick={() => navigate('/admin/users?invite=1')}
                style={{
                  marginTop: 8,
                  padding: '10px 20px',
                  background: t.primary,
                  color: '#fff',
                  border: 'none',
                  borderRadius: t.radiusMd,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                最初の招待を送る
              </button>
            </div>
          ) : (
            <div
              style={{
                background: t.surface,
                border: `1px solid ${t.border}`,
                borderRadius: t.radiusLg,
                overflow: 'auto',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${t.border}` }}>
                    {['メールアドレス', '権限', 'ステータス', '有効期限', 'アクション'].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: '12px 16px',
                          textAlign: 'left',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          color: t.textMuted,
                          letterSpacing: '0.05em',
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((inv) => {
                    const busy = actionLoading === inv.id
                    return (
                      <tr
                        key={inv.id}
                        style={{
                          borderBottom: `1px solid ${t.border}`,
                          opacity: busy ? 0.6 : 1,
                          transition: 'background 150ms',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = t.bg
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'transparent'
                        }}
                      >
                        {/* Email */}
                        <td
                          style={{
                            padding: '12px 16px',
                            fontSize: '0.9rem',
                            color: t.text,
                            maxWidth: 240,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {inv.email}
                        </td>
                        {/* Role */}
                        <td style={{ padding: '12px 16px' }}>
                          <RoleBadge role={inv.role} />
                        </td>
                        {/* Status */}
                        <td style={{ padding: '12px 16px' }}>
                          <StatusBadge status={inv.effective_status as EffectiveStatus} />
                        </td>
                        {/* Expiry */}
                        <td style={{ padding: '12px 16px' }}>
                          <ExpiryCell
                            expiresAt={inv.expires_at}
                            status={inv.effective_status as EffectiveStatus}
                          />
                        </td>
                        {/* Actions */}
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', gap: 8 }}>
                            {inv.effective_status === 'pending' && (
                              <>
                                <button
                                  onClick={() => handleResend(inv)}
                                  disabled={busy}
                                  title="招待メールを再送する"
                                  style={{
                                    padding: '5px 12px',
                                    border: `1.5px solid ${t.border}`,
                                    borderRadius: t.radiusMd,
                                    background: t.surface,
                                    color: t.text,
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    cursor: busy ? 'not-allowed' : 'pointer',
                                  }}
                                >
                                  再送
                                </button>
                                <button
                                  onClick={() => handleRevoke(inv)}
                                  disabled={busy}
                                  title="招待を取り消す"
                                  style={{
                                    padding: '5px 12px',
                                    border: `1.5px solid #fecaca`,
                                    borderRadius: t.radiusMd,
                                    background: '#fef2f2',
                                    color: t.danger,
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    cursor: busy ? 'not-allowed' : 'pointer',
                                  }}
                                >
                                  取消
                                </button>
                              </>
                            )}
                            {inv.effective_status !== 'pending' && (
                              <span style={{ fontSize: '0.8rem', color: t.textMuted }}>—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
