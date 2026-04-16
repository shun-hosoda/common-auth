import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
import { type MfaSettings, getMfaSettings, updateMfaSettings } from '../api/adminApi'
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
  MdSecurity, MdWarning,
} from 'react-icons/md'

/* ─── SecuritySettings ─────────────────────────────────── */
export default function SecuritySettings() {
  const { user, logout, hasRole, getAccessToken } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isSuperAdmin  = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin       = isSuperAdmin || isTenantAdmin

  const profile    = user?.profile as Record<string, unknown> | undefined
  const email      = (profile?.email as string) ?? ''
  const name       = (profile?.name as string) || (profile?.preferred_username as string) || email
  const initial    = name.charAt(0).toUpperCase() || '?'
  const rawTenantId = profile?.tenant_id
  const tenantName  = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) ?? ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

  /* ---- MFA form state ---- */
  const [loading, setLoading]       = useState(true)
  const [saving, setSaving]         = useState(false)
  const [error, setError]           = useState<string | null>(null)
  const [success, setSuccess]       = useState<string | null>(null)
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [mfaMethod, setMfaMethod]   = useState('totp')
  // Track the initial (server) value to detect changes for confirm dialog
  const [serverEnabled, setServerEnabled] = useState(false)

  /* ---- Confirm dialog ---- */
  const [showConfirm, setShowConfirm] = useState(false)
  const [confirmAction, setConfirmAction] = useState<'enable' | 'disable'>('enable')

  /* ---- Fetch settings ---- */
  const fetchSettings = useCallback(async () => {
    const token = getAccessToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data: MfaSettings = await getMfaSettings(token)
      setMfaEnabled(data.mfa_enabled)
      setMfaMethod(data.mfa_method)
      setServerEnabled(data.mfa_enabled)
    } catch (e) {
      setError(e instanceof Error ? e.message : '設定の読み込みに失敗しました')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { fetchSettings() }, [fetchSettings])

  /* ---- Save handler ---- */
  const handleSave = async () => {
    setShowConfirm(false)
    const token = getAccessToken()
    if (!token) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await updateMfaSettings(token, {
        mfa_enabled: mfaEnabled,
        mfa_method: mfaMethod,
      })
      setServerEnabled(result.mfa_enabled)
      const failMsg = result.users_failed > 0
        ? `（${result.users_failed}名の更新に失敗）`
        : ''
      setSuccess(`✅ MFA設定を更新しました（${result.users_updated}名に適用${failMsg}）`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  /* ---- Save with confirmation ---- */
  const onSaveClick = () => {
    // Detect enable/disable change that requires confirmation
    if (mfaEnabled !== serverEnabled) {
      setConfirmAction(mfaEnabled ? 'enable' : 'disable')
      setShowConfirm(true)
      return
    }
    // No toggle change — save directly
    handleSave()
  }

  /* ---- Layout ---- */
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

        <UserDropdown initial={initial} name={name} email={email} items={dropdownItems} />
      </header>

      {/* ── Mobile Drawer ── */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navItems}
        currentPath="/security"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      {/* ── Body ── */}
      <div style={{ display: 'flex' }}>
        {!isMobile && (
          <SideNav items={navItems} currentPath="/security" onNavigate={navigate} />
        )}

        <main style={{ flex: 1, minWidth: 0, padding: isMobile ? '16px' : '24px' }}>

          {/* Page header */}
          <h1 style={{ margin: '0 0 20px', fontSize: '1.25rem', fontWeight: 700, color: t.text }}>
            <MdLock style={{ verticalAlign: 'middle', marginRight: 6 }} /> セキュリティ設定
          </h1>

          {/* Loading */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem', color: t.textMuted }}>読み込み中...</div>
          )}

          {/* Error banner */}
          {error && (
            <div style={{
              background: '#fee2e2', color: '#b91c1c', padding: '0.75rem 1rem',
              borderRadius: t.radiusMd, marginBottom: '16px', fontSize: '0.875rem',
            }}>
              <strong>エラー:</strong> {error}
            </div>
          )}

          {/* Success banner */}
          {success && (
            <div style={{
              background: '#dcfce7', color: '#15803d', padding: '0.75rem 1rem',
              borderRadius: t.radiusMd, marginBottom: '16px', fontSize: '0.875rem',
            }}>
              {success}
            </div>
          )}

          {/* MFA Settings Card */}
          {!loading && (
            <div style={{
              background: t.surface, border: `1px solid ${t.border}`,
              borderRadius: t.radiusLg, padding: '24px', boxShadow: t.shadowSm,
            }}>
              <h2 style={{ margin: '0 0 20px', fontSize: '1.1rem', fontWeight: 600, color: t.text }}>
                MFA（多要素認証）
              </h2>

              {/* Toggle */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                <span style={{ fontSize: '0.95rem', fontWeight: 500, color: t.text }}>MFA を有効にする</span>
                <button
                  role="switch"
                  aria-checked={mfaEnabled}
                  onClick={() => setMfaEnabled(v => !v)}
                  style={{
                    width: 48, height: 26, borderRadius: 13,
                    background: mfaEnabled ? t.primary : '#cbd5e1',
                    border: 'none', cursor: 'pointer', position: 'relative',
                    transition: 'background 200ms',
                  }}
                >
                  <span style={{
                    position: 'absolute', top: 3,
                    left: mfaEnabled ? 25 : 3,
                    width: 20, height: 20, borderRadius: '50%',
                    background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                    transition: 'left 200ms',
                  }} />
                </button>
              </div>

              {/* Radio: MFA Method */}
              <fieldset style={{ border: 'none', margin: 0, padding: 0, marginBottom: '24px' }}>
                <legend style={{ fontSize: '0.9rem', fontWeight: 600, color: t.text, marginBottom: '12px' }}>
                  MFA方式
                </legend>

                {/* TOTP */}
                <label style={{
                  display: 'flex', alignItems: 'flex-start', gap: '10px',
                  padding: '12px', borderRadius: t.radiusMd, marginBottom: '8px',
                  border: `1px solid ${mfaMethod === 'totp' ? t.primary : t.border}`,
                  background: mfaMethod === 'totp' ? '#eff6ff' : 'transparent',
                  cursor: 'pointer',
                }}>
                  <input
                    type="radio"
                    name="mfa_method"
                    value="totp"
                    checked={mfaMethod === 'totp'}
                    onChange={() => setMfaMethod('totp')}
                    style={{ marginTop: '2px' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem', color: t.text }}>TOTP（認証アプリ）</div>
                    <div style={{ fontSize: '0.8rem', color: t.textMuted, marginTop: '2px' }}>
                      Google Authenticator 等でワンタイムコードを生成
                    </div>
                  </div>
                </label>

                {/* Email OTP (disabled) */}
                <label
                  aria-describedby="email-otp-note"
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: '10px',
                    padding: '12px', borderRadius: t.radiusMd,
                    border: `1px solid ${t.border}`,
                    background: '#f8fafc',
                    cursor: 'not-allowed', opacity: 0.6,
                  }}
                >
                  <input
                    type="radio"
                    name="mfa_method"
                    value="email"
                    disabled
                    style={{ marginTop: '2px' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem', color: t.textMuted }}>
                      メールOTP
                      <span style={{
                        marginLeft: '8px', fontSize: '0.7rem', fontWeight: 600,
                        padding: '2px 6px', borderRadius: '4px',
                        background: '#f1f5f9', color: t.textMuted,
                      }}>
                        準備中
                      </span>
                    </div>
                    <div id="email-otp-note" style={{ fontSize: '0.8rem', color: t.textMuted, marginTop: '2px' }}>
                      Keycloak 26以降で対応予定
                    </div>
                  </div>
                </label>
              </fieldset>

              {/* Save button */}
              <button
                onClick={onSaveClick}
                disabled={saving}
                style={{
                  padding: '10px 24px', borderRadius: t.radiusMd,
                  background: t.primary, color: t.textInverse,
                  border: 'none', cursor: saving ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem', fontWeight: 600,
                  opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? '保存中...' : '保存する'}
              </button>

              {/* Info note */}
              <div style={{
                marginTop: '20px', padding: '12px 16px',
                background: '#f0f9ff', borderRadius: t.radiusMd,
                fontSize: '0.8rem', color: '#1e40af', lineHeight: 1.6,
              }}>
                ⓘ 設定はテナント全体に適用されます。次回ログイン時からMFAが要求されます。
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── Confirm Dialog ── */}
      {showConfirm && (
        <div
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowConfirm(false) }}
          onKeyDown={(e) => { if (e.key === 'Escape') setShowConfirm(false) }}
        >
          <div style={{
            background: t.surface, borderRadius: 12, padding: '2rem',
            width: '100%', maxWidth: 420, boxShadow: t.shadowMd,
          }}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
                {confirmAction === 'enable' ? <MdSecurity /> : <MdWarning />}
              </div>
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem' }}>
                {confirmAction === 'enable' ? 'MFAを有効にする' : 'MFAを無効にする'}
              </h2>
              <p style={{ margin: 0, color: t.textMuted, fontSize: '0.875rem', lineHeight: 1.6 }}>
                {confirmAction === 'enable'
                  ? 'MFAを有効にすると、テナント内の全ユーザーに次回ログイン時からMFAが要求されます。'
                  : 'MFAを無効にすると、テナント内の全ユーザーのMFA要求が解除されます。'}
              </p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setShowConfirm(false)}
                style={{
                  padding: '8px 16px', borderRadius: t.radiusMd,
                  background: 'none', border: `1px solid ${t.border}`,
                  fontSize: '0.875rem', cursor: 'pointer', color: t.text,
                }}
              >
                キャンセル
              </button>
              <button
                onClick={handleSave}
                style={{
                  padding: '8px 20px', borderRadius: t.radiusMd,
                  background: confirmAction === 'enable' ? t.primary : t.danger,
                  color: t.textInverse, border: 'none', cursor: 'pointer',
                  fontSize: '0.875rem', fontWeight: 600,
                }}
              >
                {confirmAction === 'enable' ? '有効にする' : '無効にする'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
