import { useEffect, useRef, useState } from 'react'
import { t } from '../theme/tokens'

// ─── useIsMobile ────────────────────────────────────────────────────────────
export function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= breakpoint)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= breakpoint)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [breakpoint])
  return isMobile
}

// ─── Avatar ─────────────────────────────────────────────────────────────────
export function Avatar({ initial, size = 36 }: { initial: string; size?: number }) {
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

// ─── UserDropdown ───────────────────────────────────────────────────────────
export interface DropdownItem {
  label: string
  icon: string
  onClick: () => void
  danger?: boolean
}

export function UserDropdown({
  initial, name, email, items,
}: {
  initial: string; name: string; email: string
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
            <div style={{ fontSize: '0.78rem', color: t.textMuted }}>{email}</div>
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

// ─── SideNav ────────────────────────────────────────────────────────────────
export interface NavItem { label: string; icon: string; path: string }

export function SideNav({ items, currentPath, onNavigate }: {
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

// ─── MobileDrawer ───────────────────────────────────────────────────────────
export function MobileDrawer({ open, onClose, items, currentPath, onNavigate, tenantTitle }: {
  open: boolean; onClose: () => void
  items: NavItem[]; currentPath: string; onNavigate: (path: string) => void
  tenantTitle: string
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
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: t.text }}>{tenantTitle}</span>
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
