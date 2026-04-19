import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'
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
  MdGroup, MdHistory,
} from 'react-icons/md'

/* ─── Dashboard (main) ──────────────────────────────────── */
export default function Dashboard() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const email   = (user?.profile?.email as string)              || '—'
  const name    = (user?.profile?.name as string)
               || (user?.profile?.preferred_username as string)
               || email
  const initial = name.charAt(0).toUpperCase()

  const isSuperAdmin  = hasRole('super_admin')
  const isTenantAdmin = hasRole('tenant_admin')
  const isAdmin       = isSuperAdmin || isTenantAdmin

  const rawTenantId = user?.profile?.tenant_id
  const tenantName  = Array.isArray(rawTenantId) ? rawTenantId[0] : (rawTenantId as string | undefined) || ''
  const tenantTitle = tenantName || (isSuperAdmin ? '全テナント管理' : 'Common Auth')

  /* ---- Side navigation items (admin only) ---- */
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

  /* ---- User dropdown items ---- */
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
          initial={initial}
          name={name}
          email={email}
          items={dropdownItems}
        />
      </header>

      {/* ── Mobile Drawer ── */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        items={navItems}
        currentPath="/dashboard"
        onNavigate={navigate}
        tenantTitle={tenantTitle}
      />

      {/* ── Body ── */}
      <div style={{ display: 'flex' }}>

        {/* PC SideNav */}
        {!isMobile && (
          <SideNav
            items={navItems}
            currentPath="/dashboard"
            onNavigate={navigate}
          />
        )}

        {/* Main — メインコンテンツ */}
        <main style={{
          flex: 1, minWidth: 0,
          padding: isMobile ? '16px' : '32px 24px',
        }}>
        </main>
      </div>
    </div>
  )
}
