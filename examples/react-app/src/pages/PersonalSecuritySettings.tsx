import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import { type MfaStatus, getMfaStatus } from '../api/adminApi'
import { t } from '../theme/tokens'
import { ChangePasswordModal } from '../components/ChangePasswordModal'
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
} from 'react-icons/md'

export default function PersonalSecuritySettings() {
  const { user, logout, hasRole, getAccessToken } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const [status, setStatus] = useState<MfaStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Password change modal
  const [modalOpen, setModalOpen] = useState(false)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = (msg: string) => {
    setToastMsg(msg)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToastMsg(null), 3000)
  }

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [])

  const isSuperAdmin = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin = isSuperAdmin || isTenantAdmin

  const profile = user?.profile as Record<string, unknown> | undefined
  const email = (profile?.email as string) ?? ''
  const name = (profile?.name as string) || (profile?.preferred_username as string) || email
  const initial = name.charAt(0).toUpperCase() || '?'
  const rawTenantId = profile?.tenant_id
  const tenantName = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) ?? ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const token = getAccessToken()
      if (!token) {
        setLoading(false)
        return
      }
      setLoading(true)
      setError(null)
      try {
        const data = await getMfaStatus(token)
        if (!cancelled) setStatus(data)
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : '読み込みに失敗しました')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [getAccessToken])

  const navItems: NavItem[] = [
    { label: 'ダッシュボード', icon: <MdHome />, path: '/dashboard' },
    ...(isAdmin ? [{ label: 'ユーザー管理', icon: <MdPeople />, path: '/admin/users' }] : []),
    ...(isAdmin ? [{ label: 'セキュリティ設定', icon: <MdLock />, path: '/security' }] : []),
    ...(isSuperAdmin ? [{ label: 'テナント管理', icon: <MdBusiness />, path: '/admin/clients' }] : []),
  ]

  const dropdownItems: DropdownItem[] = [
    { label: '個人セキュリティ設定', icon: <MdManageAccounts />, onClick: () => navigate('/me/security') },
    { label: 'ログアウト', icon: <MdLogout />, onClick: logout, danger: true },
  ]

  const statusLabel = !status
    ? '不明'
    : !status.mfa_enabled
      ? 'MFA 無効'
      : status.mfa_configured
        ? 'MFA 設定済み'
        : 'MFA 未設定'

  return (
    <div style={{ minHeight: '100vh', background: t.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
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
        <UserDropdown initial={initial} name={name} email={email} items={dropdownItems} />
      </header>

      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navItems}
        currentPath="/me/security"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      <div style={{ display: 'flex' }}>
        {!isMobile && (
          <SideNav
            items={navItems}
            currentPath="/me/security"
            onNavigate={navigate}
          />
        )}

        <main style={{ flex: 1, minWidth: 0, padding: isMobile ? '16px' : '24px' }}>
          <h1 style={{ margin: '0 0 20px', fontSize: '1.25rem', fontWeight: 700, color: t.text }}>
            <MdManageAccounts style={{ verticalAlign: 'middle', marginRight: 6 }} /> 個人セキュリティ設定
          </h1>

          {loading && <div style={{ color: t.textMuted }}>読み込み中...</div>}

          {error && (
            <div style={{
              background: '#fee2e2', color: '#b91c1c', padding: '0.75rem 1rem',
              borderRadius: t.radiusMd, marginBottom: '16px', fontSize: '0.875rem',
            }}>
              <strong>エラー:</strong> {error}
            </div>
          )}

          {/* Success toast */}
          {toastMsg && (
            <div
              role="status"
              aria-live="polite"
              style={{
                position: 'fixed',
                bottom: '24px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: t.success,
                color: '#fff',
                padding: '12px 24px',
                borderRadius: t.radiusFull,
                fontWeight: 600,
                fontSize: '0.9rem',
                boxShadow: t.shadowMd,
                zIndex: 2000,
                whiteSpace: 'nowrap',
              }}
            >
              ✅ {toastMsg}
            </div>
          )}

          {/* Password change modal */}
          <ChangePasswordModal
            open={modalOpen}
            token={getAccessToken() ?? ''}
            onClose={() => setModalOpen(false)}
            onSuccess={() => {
              setModalOpen(false)
              showToast('パスワードを変更しました')
            }}
          />

          {!loading && (
            <>
            <div style={{
              background: t.surface, border: `1px solid ${t.border}`,
              borderRadius: t.radiusLg, padding: '24px', boxShadow: t.shadowSm,
            }}>
              <h2 style={{ margin: '0 0 16px', fontSize: '1.05rem', fontWeight: 600, color: t.text }}>
                MFA（二要素認証）
              </h2>

              <div style={{ marginBottom: '16px', color: t.text, fontSize: '0.92rem' }}>
                現在の状態: <strong>{statusLabel}</strong>
                {status?.mfa_enabled && (
                  <span style={{ color: t.textMuted }}>（方式: {status.mfa_method === 'totp' ? 'TOTP' : status.mfa_method}）</span>
                )}
              </div>

              {!status?.mfa_enabled && (
                <div style={{
                  padding: '10px 16px', borderRadius: t.radiusMd,
                  background: '#f1f5f9', color: t.textMuted,
                  fontSize: '0.875rem',
                }}>
                  MFAはテナント管理者によって有効化されていません
                </div>
              )}

              <div style={{
                marginTop: '18px', padding: '12px 16px',
                background: '#f8fafc', borderRadius: t.radiusMd,
                fontSize: '0.82rem', color: t.textMuted, lineHeight: 1.6,
              }}>
                {status?.mfa_enabled
                  ? 'MFAが有効です。MFAの設定・再設定はテナント管理者にお問い合わせください。'
                  : 'MFAを利用するには、テナント管理者がセキュリティ設定画面からMFAを有効化する必要があります。'}
              </div>
            </div>

            {/* パスワード変更セクション */}
            <div style={{
              background: t.surface, border: `1px solid ${t.border}`,
              borderRadius: t.radiusLg, padding: '24px', boxShadow: t.shadowSm,
              marginTop: '16px',
            }}>
              <h2 style={{ margin: '0 0 8px', fontSize: '1.05rem', fontWeight: 600, color: t.text }}>
                パスワード
              </h2>
              <p style={{ margin: '0 0 16px', fontSize: '0.875rem', color: t.textMuted }}>
                現在のパスワードを変更します。変更後は現在のセッションが維持されます。
              </p>
              <button
                onClick={() => setModalOpen(true)}
                style={{
                  padding: '10px 16px', borderRadius: t.radiusMd,
                  background: t.primary, color: t.textInverse,
                  border: 'none', cursor: 'pointer', fontWeight: 600,
                }}
              >
                パスワードを変更する
              </button>
              <div style={{
                marginTop: '18px', padding: '12px 16px',
                background: '#f8fafc', borderRadius: t.radiusMd,
                fontSize: '0.82rem', color: t.textMuted, lineHeight: 1.6,
              }}>
                現在のパスワードを知っている場合に使用します。パスワードを忘れた場合は、ログアウト後にログイン画面の「パスワードをお忘れの方」をご利用ください。
              </div>
            </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
