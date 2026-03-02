import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

/* ─── Design Tokens ─────────────────────────────────────── */
const t = {
  primary:     '#2563eb',
  success:     '#16a34a',
  danger:      '#dc2626',
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

/* ─── Role Config ───────────────────────────────────────── */
const ROLE_CONFIG = {
  super_admin:  { label: 'スーパー管理者', color: t.danger },
  tenant_admin: { label: 'テナント管理者', color: t.primary },
  user:         { label: '一般ユーザー',   color: t.success },
}

function resolveRole(isSuperAdmin: boolean, isTenantAdmin: boolean) {
  if (isSuperAdmin)  return ROLE_CONFIG.super_admin
  if (isTenantAdmin) return ROLE_CONFIG.tenant_admin
  return ROLE_CONFIG.user
}

/* ─── useIsMobile ───────────────────────────────────────── */
function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= breakpoint)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= breakpoint)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [breakpoint])
  return isMobile
}

/* ─── Avatar ────────────────────────────────────────────── */
function Avatar({ initial, size = 36 }: { initial: string; size?: number }) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: size, height: size, flexShrink: 0,
        borderRadius: t.radiusFull,
        background: t.primary, color: t.textInverse,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontWeight: 700, fontSize: size * 0.42,
        userSelect: 'none',
      }}
    >
      {initial}
    </div>
  )
}

/* ─── Badge ─────────────────────────────────────────────── */
function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span role="status" style={{
      padding: '3px 10px', borderRadius: t.radiusFull,
      background: color, color: t.textInverse,
      fontSize: '0.72rem', fontWeight: 600, whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}

/* ─── UserDropdown ──────────────────────────────────────── */
interface DropdownItem {
  label: string
  icon: string
  onClick: () => void
  danger?: boolean
}

function UserDropdown({
  initial, name, email, roleLabel, roleColor, items,
}: {
  initial: string; name: string; email: string
  roleLabel: string; roleColor: string
  items: DropdownItem[]
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="ユーザーメニューを開く"
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          background: 'none', border: 'none', cursor: 'pointer',
          padding: '4px 8px', borderRadius: t.radiusMd,
          transition: 'background 150ms',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = t.bg }}
        onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
      >
        <Avatar initial={initial} size={34} />
        <span style={{ fontSize: '0.875rem', color: t.text, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {name}
        </span>
        <span style={{ fontSize: '0.65rem', color: t.textMuted }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div
          role="menu"
          style={{
            position: 'absolute', right: 0, top: 'calc(100% + 6px)',
            background: t.surface, border: `1px solid ${t.border}`,
            borderRadius: t.radiusLg, boxShadow: t.shadowMd,
            minWidth: 200, zIndex: 200, overflow: 'hidden',
          }}
        >
          {/* User info header */}
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${t.border}` }}>
            <div style={{ fontWeight: 600, fontSize: '0.875rem', color: t.text, marginBottom: 4 }}>{name}</div>
            <div style={{ fontSize: '0.78rem', color: t.textMuted, marginBottom: 8 }}>{email}</div>
            <Badge label={roleLabel} color={roleColor} />
          </div>

          {/* Menu items */}
          {items.map((item) => (
            <button
              key={item.label}
              role="menuitem"
              onClick={() => { setOpen(false); item.onClick() }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                padding: '11px 16px', background: 'none', border: 'none',
                cursor: 'pointer', textAlign: 'left',
                fontSize: '0.875rem',
                color: item.danger ? t.danger : t.text,
                transition: 'background 120ms',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = t.bg }}
              onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── SideNav ───────────────────────────────────────────── */
interface NavItem { label: string; icon: string; path: string }

function SideNav({ items, currentPath, onNavigate }: {
  items: NavItem[]; currentPath: string; onNavigate: (path: string) => void
}) {
  return (
    <nav aria-label="サイドメニュー" style={{
      width: 220, flexShrink: 0,
      background: t.surface, borderRight: `1px solid ${t.border}`,
      padding: '16px 8px',
      minHeight: 'calc(100vh - 60px)',
    }}>
      {items.map(item => {
        const active = currentPath === item.path
        return (
          <button
            key={item.path}
            onClick={() => onNavigate(item.path)}
            aria-current={active ? 'page' : undefined}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
              padding: '10px 12px', borderRadius: t.radiusMd,
              background: active ? '#dbeafe' : 'none',
              color: active ? t.primary : t.text,
              border: 'none', cursor: 'pointer', textAlign: 'left',
              fontSize: '0.875rem', fontWeight: active ? 600 : 400,
              transition: 'background 120ms',
              marginBottom: 2, minHeight: 44,
            }}
            onMouseEnter={e => { if (!active) e.currentTarget.style.background = t.bg }}
            onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'none' }}
          >
            <span aria-hidden="true" style={{ fontSize: '1rem' }}>{item.icon}</span>
            {item.label}
          </button>
        )
      })}
    </nav>
  )
}

/* ─── MobileNav (bottom sheet drawer) ──────────────────── */
function MobileDrawer({ open, onClose, items, currentPath, onNavigate }: {
  open: boolean; onClose: () => void
  items: NavItem[]; currentPath: string; onNavigate: (path: string) => void
}) {
  if (!open) return null
  return (
    <>
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgb(0 0 0 / 0.35)', zIndex: 300 }}
      />
      <nav
        aria-label="モバイルメニュー"
        style={{
          position: 'fixed', left: 0, top: 0, bottom: 0, width: 260,
          background: t.surface, zIndex: 400,
          padding: '24px 8px', boxShadow: t.shadowMd,
          display: 'flex', flexDirection: 'column', gap: 2,
        }}
      >
        <div style={{ padding: '0 12px 16px', borderBottom: `1px solid ${t.border}`, marginBottom: 8 }}>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: t.primary }}>🔐 Common Auth</span>
        </div>
        {items.map(item => {
          const active = currentPath === item.path
          return (
            <button
              key={item.path}
              onClick={() => { onClose(); onNavigate(item.path) }}
              aria-current={active ? 'page' : undefined}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '12px 16px', borderRadius: t.radiusMd,
                background: active ? '#dbeafe' : 'none',
                color: active ? t.primary : t.text,
                border: 'none', cursor: 'pointer', textAlign: 'left',
                fontSize: '0.9rem', fontWeight: active ? 600 : 400,
                minHeight: 48,
              }}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          )
        })}
      </nav>
    </>
  )
}

/* ─── WelcomeCard ───────────────────────────────────────── */
function WelcomeCard({ initial, name, email, roleLabel, roleColor }: {
  initial: string; name: string; email: string; roleLabel: string; roleColor: string
}) {
  return (
    <div style={{
      background: t.surface, border: `1px solid ${t.border}`,
      borderRadius: t.radiusLg, padding: '28px 24px',
      boxShadow: t.shadowSm,
      display: 'flex', alignItems: 'center', gap: '16px',
      flexWrap: 'wrap',
    }}>
      <Avatar initial={initial} size={56} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700, color: t.text }}>
          ようこそ、{name}
        </h1>
        <p style={{ margin: '0 0 10px', fontSize: '0.875rem', color: t.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {email}
        </p>
        <Badge label={roleLabel} color={roleColor} />
      </div>
    </div>
  )
}

/* ─── Dashboard (main) ──────────────────────────────────── */
export default function Dashboard() {
  const { user, logout, configureMFA, getAccessToken, hasRole } = useAuth()
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
  const isDev         = import.meta.env.DEV

  const roleConfig = resolveRole(isSuperAdmin, isTenantAdmin)

  /* ---- Side navigation items (admin only) ---- */
  const navItems: NavItem[] = [
    { label: 'ダッシュボード', icon: '🏠', path: '/dashboard' },
    ...(isAdmin ? [{ label: 'ユーザー管理', icon: '👥', path: '/admin/users' }] : []),
    ...(isSuperAdmin ? [{ label: 'テナント管理', icon: '🏢', path: '/admin/tenants' }] : []),
  ]

  /* ---- User dropdown items ---- */
  const dropdownItems: DropdownItem[] = [
    { label: 'セキュリティ設定', icon: '🔒', onClick: configureMFA },
    ...(isDev ? [{ label: 'アクセストークンをコピー', icon: '🔑', onClick: () => {
      const token = getAccessToken(); if (token) { navigator.clipboard.writeText(token); alert('コピーしました') }
    }}] : []),
    { label: 'ログアウト', icon: '🚪', onClick: logout, danger: true },
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
          <span style={{ fontSize: '1rem', fontWeight: 700, color: t.primary }}>🔐 Common Auth</span>
        </div>

        <UserDropdown
          initial={initial}
          name={name}
          email={email}
          roleLabel={roleConfig.label}
          roleColor={roleConfig.color}
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

        {/* Main */}
        <main style={{
          flex: 1, minWidth: 0,
          padding: isMobile ? '16px' : '32px 24px',
          maxWidth: 720,
        }}>
          <WelcomeCard
            initial={initial}
            name={name}
            email={email}
            roleLabel={roleConfig.label}
            roleColor={roleConfig.color}
          />
        </main>
      </div>
    </div>
  )
}
