/**
 * InviteUsers ページ (/admin/users/invite)
 *
 * メールアドレスを複数入力して招待を一括送信する。
 * 権限: tenant_admin / super_admin のみ（AuthGuard で保護）
 */

import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import {
  type InvitationBulkResponse,
  type InvitationFailedItem,
  type InvitationResponse,
  createInvitations,
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

// ─── Styles ───────────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.875rem',
  fontWeight: 600,
  color: t.text,
  marginBottom: 6,
}
const inputBase: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: `1.5px solid ${t.border}`,
  borderRadius: t.radiusMd,
  fontSize: '0.95rem',
  color: t.text,
  background: t.surface,
  boxSizing: 'border-box',
  outline: 'none',
}
const selectBase: React.CSSProperties = {
  ...inputBase,
  appearance: 'none',
  cursor: 'pointer',
}

// ─── Success/Failed result card ───────────────────────────────────────────────

function ResultCard({ result }: { result: InvitationBulkResponse }) {
  return (
    <div>
      {result.succeeded.length > 0 && (
        <div
          style={{
            background: '#f0fdf4',
            border: `1px solid #bbf7d0`,
            borderRadius: t.radiusMd,
            padding: '1rem',
            marginBottom: '1rem',
          }}
        >
          <div style={{ fontWeight: 600, color: t.success, marginBottom: 8 }}>
            ✅ 送信成功 ({result.succeeded.length}件)
          </div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {result.succeeded.map((inv: InvitationResponse) => (
              <li key={inv.id} style={{ fontSize: '0.875rem', color: '#166534' }}>
                {inv.email}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.failed.length > 0 && (
        <div
          style={{
            background: '#fef2f2',
            border: `1px solid #fecaca`,
            borderRadius: t.radiusMd,
            padding: '1rem',
          }}
        >
          <div style={{ fontWeight: 600, color: t.danger, marginBottom: 8 }}>
            ❌ 送信失敗 ({result.failed.length}件)
          </div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {result.failed.map((item: InvitationFailedItem) => (
              <li key={item.email} style={{ fontSize: '0.875rem', color: '#991b1b' }}>
                {item.email} — {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function InviteUsers() {
  const { user, getAccessToken, logout } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const [emailsText, setEmailsText] = useState('')
  const [role, setRole] = useState<'user' | 'tenant_admin'>('user')
  const [customMessage, setCustomMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<InvitationBulkResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const hasAdminRole = useMemo(() => {
    const roles: string[] = (user as any)?.roles ?? []
    return roles.includes('tenant_admin') || roles.includes('super_admin')
  }, [user])

  const emailList = useMemo(() => {
    return emailsText
      .split(/[\n,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0)
  }, [emailsText])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (emailList.length === 0) return
      setError(null)
      setResult(null)
      setSubmitting(true)
      try {
        const token = getAccessToken()
        if (!token) return
        // S-5 fix: custom_message is a bulk-level field on InvitationBulkRequest,
        // not a per-recipient field on InvitationCreateItem
        const res = await createInvitations(token, {
          invitations: emailList.map((email) => ({ email, role })),
          custom_message: customMessage.trim() || undefined,
        })
        setResult(res)
        if (res.failed.length === 0) {
          // 全件成功 → フォームリセット
          setEmailsText('')
          setCustomMessage('')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '招待の送信に失敗しました')
      } finally {
        setSubmitting(false)
      }
    },
    [emailList, role, customMessage, getAccessToken],
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
        currentPath="/admin/users/invite"
        onNavigate={navigate}
        tenantTitle="Common Auth"
      />

      <div style={{ display: 'flex', flex: 1 }}>
        {/* SideNav (desktop) */}
        {!isMobile && (
          <SideNav
            items={navList}
            currentPath="/admin/users/invite"
            onNavigate={navigate}
          />
        )}

        {/* Main content */}
        <main style={{ flex: 1, padding: isMobile ? '1rem' : '2rem', maxWidth: 680 }}>
          {/* Back link */}
          <button
            onClick={() => navigate('/admin/users')}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: t.primary,
              fontSize: '0.875rem',
              padding: 0,
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            ← ユーザー管理に戻る
          </button>

          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: t.text, marginBottom: 8 }}>
            ユーザーを招待
          </h1>
          <p style={{ color: t.textMuted, marginBottom: '2rem', fontSize: '0.9rem' }}>
            招待メールを送信します。受信者はリンクをクリックしてアカウントを作成できます。
          </p>

          {/* Result card */}
          {result && <ResultCard result={result} />}

          {error && (
            <div
              style={{
                background: '#fef2f2',
                border: `1px solid #fecaca`,
                borderRadius: t.radiusMd,
                padding: '1rem',
                color: t.danger,
                marginBottom: '1rem',
                fontSize: '0.9rem',
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div
              style={{
                background: t.surface,
                border: `1px solid ${t.border}`,
                borderRadius: t.radiusLg,
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
              }}
            >
              {/* Email input */}
              <div>
                <label style={labelStyle} htmlFor="emails">
                  メールアドレス *
                </label>
                <textarea
                  id="emails"
                  value={emailsText}
                  onChange={(e) => setEmailsText(e.target.value)}
                  placeholder={'複数のアドレスはカンマまたは改行で区切ってください\nexample1@example.com\nexample2@example.com'}
                  rows={4}
                  required
                  style={{ ...inputBase, resize: 'vertical', fontFamily: 'inherit' }}
                />
                {emailList.length > 0 && (
                  <p style={{ fontSize: '0.8rem', color: t.textMuted, marginTop: 4 }}>
                    {emailList.length}件のアドレスを検出
                  </p>
                )}
              </div>

              {/* Role */}
              <div>
                <label style={labelStyle} htmlFor="role">
                  権限
                </label>
                <select
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as 'user' | 'tenant_admin')}
                  style={selectBase}
                >
                  <option value="user">一般ユーザー</option>
                  <option value="tenant_admin">テナント管理者</option>
                </select>
              </div>

              {/* Custom message */}
              <div>
                <label style={labelStyle} htmlFor="message">
                  メッセージ（任意）
                </label>
                <textarea
                  id="message"
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  placeholder="招待メールに添付するメッセージを入力（省略可）"
                  rows={3}
                  maxLength={500}
                  style={{ ...inputBase, resize: 'vertical', fontFamily: 'inherit' }}
                />
                {customMessage.length > 0 && (
                  <p style={{ fontSize: '0.8rem', color: t.textMuted, marginTop: 4 }}>
                    {customMessage.length}/500文字
                  </p>
                )}
              </div>

              {/* Submit */}
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => navigate('/admin/users')}
                  disabled={submitting}
                  style={{
                    padding: '10px 20px',
                    borderRadius: t.radiusMd,
                    border: `1.5px solid ${t.border}`,
                    background: t.surface,
                    color: t.text,
                    fontWeight: 600,
                    cursor: submitting ? 'not-allowed' : 'pointer',
                    fontSize: '0.9rem',
                  }}
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={submitting || emailList.length === 0}
                  style={{
                    padding: '10px 24px',
                    borderRadius: t.radiusMd,
                    border: 'none',
                    background: submitting || emailList.length === 0 ? '#93c5fd' : t.primary,
                    color: '#fff',
                    fontWeight: 600,
                    cursor: submitting || emailList.length === 0 ? 'not-allowed' : 'pointer',
                    fontSize: '0.9rem',
                    minWidth: 120,
                  }}
                >
                  {submitting ? '送信中...' : `招待を送信 (${emailList.length}件)`}
                </button>
              </div>
            </div>
          </form>
        </main>
      </div>
    </div>
  )
}
