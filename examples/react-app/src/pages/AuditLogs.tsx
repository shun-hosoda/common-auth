import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import { type AuditLog, listAuditLogs } from '../api/adminApi'
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
  MdGroup, MdHistory, MdRefresh,
} from 'react-icons/md'

// ─── Action label / color ────────────────────────────────────────────────────

const ACTION_LABELS: Record<string, string> = {
  'group.create': 'グループ作成',
  'group.update': 'グループ更新',
  'group.delete': 'グループ削除',
  'group.member.add': 'メンバー追加',
  'group.member.remove': 'メンバー削除',
  'group.permission.update': '権限更新',
  'security.password_policy.update': 'パスワードポリシー更新',
  'security.session.update': 'セッション設定更新',
  'security.mfa.update': 'MFA設定更新',
  'invitation.create': 'ユーザー招待',
  'user.role.update': 'ロール更新',
}

const actionLabel = (action: string) => ACTION_LABELS[action] ?? action

function ActionBadge({ action }: { action: string }) {
  const isDelete = action.includes('.delete') || action.includes('.remove')
  const isCreate = action.includes('.create') || action.includes('.add')
  const bg = isDelete ? '#fef2f2' : isCreate ? '#f0fdf4' : '#eff6ff'
  const color = isDelete ? '#b91c1c' : isCreate ? '#166534' : '#1d4ed8'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 999,
      fontSize: '0.75rem', fontWeight: 600, background: bg, color,
    }}>
      {actionLabel(action)}
    </span>
  )
}

// ─── AuditLogs Page ───────────────────────────────────────────────────────────

const PAGE_SIZE = 30

export default function AuditLogs() {
  const { user, logout, hasRole, getAccessToken } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
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
  const tenantIdFromQuery = new URLSearchParams(location.search).get('tenant_id') ?? undefined

  // List state
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)

  const fetchLogs = useCallback(async () => {
    const token = getAccessToken()
    if (!token) return
    if (isSuperAdmin && !tenantIdFromQuery) {
      setError('super_admin で監査ログを表示するには tenant_id クエリ指定が必要です')
      setLogs([])
      setTotal(0)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await listAuditLogs(token, {
        tenant_id: isSuperAdmin ? tenantIdFromQuery : undefined,
        page,
        per_page: PAGE_SIZE,
        action: actionFilter || undefined,
        actor_id: actorFilter || undefined,
      })
      setLogs(res.logs)
      setTotal(res.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : '監査ログ取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [getAccessToken, page, actionFilter, actorFilter, isSuperAdmin, tenantIdFromQuery])

  useEffect(() => { fetchLogs() }, [fetchLogs])

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

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px', border: `1px solid ${t.border}`,
    borderRadius: t.radiusMd, fontSize: '0.875rem', color: t.text,
    boxSizing: 'border-box',
  }

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
        currentPath="/admin/audit"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      <div style={{ display: 'flex' }}>
        {!isMobile && (
          <SideNav items={navItems} currentPath="/admin/audit" onNavigate={navigate} />
        )}

        <main style={{ flex: 1, minWidth: 0, padding: '2rem' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: t.text }}>監査ログ</h1>
              <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: t.textMuted }}>
                管理操作の履歴を確認できます
              </p>
            </div>
            <button
              style={{
                border: `1px solid ${t.border}`, borderRadius: t.radiusMd,
                background: 'transparent', cursor: 'pointer', padding: '8px 14px',
                display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.875rem', color: t.textMuted,
              }}
              onClick={fetchLogs}
              title="更新"
            >
              <MdRefresh /> 更新
            </button>
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <select
              style={{ ...inputStyle, minWidth: 180 }}
              value={actionFilter}
              onChange={e => { setActionFilter(e.target.value); setPage(1) }}
            >
              <option value="">すべてのアクション</option>
              {Object.entries(ACTION_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <input
              style={{ ...inputStyle, width: 220 }}
              placeholder="操作者ID で絞り込み…"
              value={actorFilter}
              onChange={e => { setActorFilter(e.target.value); setPage(1) }}
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
            ) : logs.length === 0 ? (
              <p style={{ padding: '3rem', textAlign: 'center', color: t.textMuted }}>
                監査ログがありません
              </p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: `1px solid ${t.border}` }}>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>日時</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>アクション</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>操作者</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, fontWeight: 600 }}>対象リソース</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr
                      key={log.id}
                      style={{
                        borderBottom: i < logs.length - 1 ? `1px solid ${t.border}` : 'none',
                        cursor: 'pointer',
                      }}
                      onClick={() => setSelectedLog(log)}
                    >
                      <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: t.textMuted, whiteSpace: 'nowrap' }}>
                        {new Date(log.created_at).toLocaleString('ja-JP')}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <ActionBadge action={log.action} />
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: t.text }}>
                        {log.actor_email ?? log.actor_id ?? '—'}
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: t.textMuted }}>
                        {log.resource_type ? `${log.resource_type}${log.resource_id ? ` (${log.resource_id.slice(0, 8)}…)` : ''}` : '—'}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '0.75rem', color: t.primary }}>
                        詳細 ›
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
              <button
                style={{
                  border: `1px solid ${t.border}`, borderRadius: t.radiusMd, background: 'transparent',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer', padding: '6px 12px',
                  fontSize: '0.875rem', opacity: page <= 1 ? 0.4 : 1,
                }}
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >←</button>
              <span style={{ fontSize: '0.875rem', color: t.textMuted }}>{page} / {totalPages}（{total} 件）</span>
              <button
                style={{
                  border: `1px solid ${t.border}`, borderRadius: t.radiusMd, background: 'transparent',
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer', padding: '6px 12px',
                  fontSize: '0.875rem', opacity: page >= totalPages ? 0.4 : 1,
                }}
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >→</button>
            </div>
          )}
        </main>
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setSelectedLog(null)}
        >
          <div
            style={{ background: t.surface, borderRadius: 12, padding: '2rem', width: '100%', maxWidth: 540, boxShadow: t.shadowMd }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 1rem', color: t.text }}>監査ログ詳細</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <tbody>
                {([
                  ['ID', selectedLog.id],
                  ['日時', new Date(selectedLog.created_at).toLocaleString('ja-JP')],
                  ['アクション', actionLabel(selectedLog.action)],
                  ['操作者ID', selectedLog.actor_id ?? '—'],
                  ['操作者メール', selectedLog.actor_email ?? '—'],
                  ['リソース種別', selectedLog.resource_type ?? '—'],
                  ['リソースID', selectedLog.resource_id ?? '—'],
                  ['IPアドレス', selectedLog.ip_address ?? '—'],
                ] as [string, string][]).map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: `1px solid ${t.border}` }}>
                    <td style={{ padding: '8px 8px 8px 0', color: t.textMuted, width: 130 }}>{label}</td>
                    <td style={{ padding: '8px 0', wordBreak: 'break-all' }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {selectedLog.details && (
              <div style={{ marginTop: 16 }}>
                <p style={{ margin: '0 0 6px', fontWeight: 600, fontSize: '0.875rem' }}>詳細データ</p>
                <pre style={{
                  background: '#f8fafc', borderRadius: t.radiusMd, padding: 12,
                  fontSize: '0.8rem', overflow: 'auto', maxHeight: 200,
                  border: `1px solid ${t.border}`, margin: 0,
                }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            )}
            <div style={{ textAlign: 'right', marginTop: 20 }}>
              <button
                style={{
                  border: `1px solid ${t.border}`, borderRadius: t.radiusMd, background: 'transparent',
                  cursor: 'pointer', padding: '8px 16px', fontSize: '0.875rem', color: t.textMuted,
                }}
                onClick={() => setSelectedLog(null)}
              >閉じる</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
