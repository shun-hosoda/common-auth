# Component Implementation Examples

## Button

```tsx
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
type ButtonSize    = 'sm' | 'md' | 'lg'

const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
  primary:   { background: 'var(--color-primary)',  color: '#fff', border: 'none' },
  secondary: { background: 'transparent',           color: 'var(--color-text)', border: '1px solid var(--color-border)' },
  danger:    { background: 'var(--color-danger)',   color: '#fff', border: 'none' },
  ghost:     { background: 'transparent',           color: 'var(--color-text-muted)', border: 'none' },
}

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  sm: { padding: '4px 12px', fontSize: '0.75rem' },
  md: { padding: '8px 16px', fontSize: '0.875rem' },
  lg: { padding: '12px 24px', fontSize: '1rem' },
}

function Button({ label, icon, onClick, variant = 'primary', size = 'md', disabled }: {
  label: string; icon?: string; onClick?: () => void
  variant?: ButtonVariant; size?: ButtonSize; disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...variantStyles[variant],
        ...sizeStyles[size],
        borderRadius: 'var(--radius-md)',
        fontWeight: 500,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        transition: 'opacity 150ms',
      }}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {label}
    </button>
  )
}
```

## Card

```tsx
function Card({ children, padding = '24px', style }: {
  children: React.ReactNode; padding?: string; style?: React.CSSProperties
}) {
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding,
      boxShadow: 'var(--shadow-sm)',
      ...style,
    }}>
      {children}
    </div>
  )
}
```

## Badge

```tsx
function Badge({ label, color = 'var(--color-primary)' }: { label: string; color?: string }) {
  return (
    <span
      role="status"
      style={{
        padding: '2px 10px',
        borderRadius: 'var(--radius-full)',
        background: color,
        color: '#fff',
        fontSize: '0.75rem',
        fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}
```

## Avatar

```tsx
function Avatar({ initials, size = 40, src }: { initials: string; size?: number; src?: string }) {
  if (src) return <img src={src} alt={initials} width={size} height={size} style={{ borderRadius: '50%', objectFit: 'cover' }} />
  return (
    <div
      aria-hidden="true"
      style={{
        width: size, height: size,
        borderRadius: '50%',
        background: 'var(--color-primary)',
        color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontWeight: 700,
        fontSize: size * 0.4,
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  )
}
```

## Alert

```tsx
const alertConfig = {
  success: { bg: 'var(--color-success-light)', border: 'var(--color-success)', icon: '✅' },
  warning: { bg: 'var(--color-warning-light)', border: 'var(--color-warning)', icon: '⚠️' },
  error:   { bg: 'var(--color-danger-light)',  border: 'var(--color-danger)',  icon: '❌' },
  info:    { bg: 'var(--color-info-light)',    border: 'var(--color-info)',    icon: 'ℹ️' },
}

function Alert({ type = 'info', message }: { type?: keyof typeof alertConfig; message: string }) {
  const cfg = alertConfig[type]
  return (
    <div
      role="alert"
      style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '12px 16px',
        borderRadius: 'var(--radius-md)',
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        fontSize: '0.875rem',
      }}
    >
      <span aria-hidden="true">{cfg.icon}</span>
      {message}
    </div>
  )
}
```

## Spinner

```tsx
function Spinner({ size = 24 }: { size?: number }) {
  return (
    <div
      role="status"
      aria-label="読み込み中"
      style={{
        width: size, height: size,
        border: `${size / 8}px solid var(--color-border)`,
        borderTopColor: 'var(--color-primary)',
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }}
    />
  )
  // Add to CSS: @keyframes spin { to { transform: rotate(360deg); } }
}
```

## EmptyState

```tsx
function EmptyState({ message, action }: { message: string; action?: React.ReactNode }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '48px 24px', gap: '16px',
      color: 'var(--color-text-muted)', textAlign: 'center',
    }}>
      <span style={{ fontSize: '2.5rem' }} aria-hidden="true">📭</span>
      <p style={{ margin: 0, fontSize: '0.875rem' }}>{message}</p>
      {action}
    </div>
  )
}
```

## Modal

```tsx
function Modal({ isOpen, onClose, title, children }: {
  isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode
}) {
  if (!isOpen) return null
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgb(0 0 0 / 0.4)',
      }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px', width: '100%', maxWidth: '480px',
        boxShadow: 'var(--shadow-lg)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 id="modal-title" style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600 }}>{title}</h2>
          <button onClick={onClose} aria-label="閉じる" style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', color: 'var(--color-text-muted)' }}>×</button>
        </div>
        {children}
      </div>
    </div>
  )
}
```

## PageHeader

```tsx
function PageHeader({ title, description, actions }: {
  title: string; description?: string; actions?: React.ReactNode
}) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      marginBottom: '24px', gap: '16px',
    }}>
      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text)' }}>{title}</h1>
        {description && <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>{description}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>{actions}</div>}
    </div>
  )
}
```

## FormField

```tsx
function FormField({ label, required, error, children }: {
  label: string; required?: boolean; error?: string; children: React.ReactNode
}) {
  const id = label.replace(/\s+/g, '-').toLowerCase()
  return (
    <div style={{ marginBottom: '16px' }}>
      <label
        htmlFor={id}
        style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: 500, color: 'var(--color-text)' }}
      >
        {label}{required && <span aria-hidden="true" style={{ color: 'var(--color-danger)', marginLeft: '2px' }}>*</span>}
      </label>
      {children}
      {error && (
        <p role="alert" style={{ margin: '4px 0 0', fontSize: '0.75rem', color: 'var(--color-danger)' }}>{error}</p>
      )}
    </div>
  )
}

/* 使用例 */
<FormField label="メールアドレス" required error={errors.email}>
  <input
    id="メールアドレス"
    type="email"
    style={{
      width: '100%', padding: '8px 12px',
      border: `1px solid ${errors.email ? 'var(--color-danger)' : 'var(--color-border)'}`,
      borderRadius: 'var(--radius-md)',
      fontSize: '0.875rem',
      boxSizing: 'border-box',
    }}
  />
</FormField>
```

## Table

```tsx
function Table<T extends Record<string, unknown>>({ columns, rows, onRowClick }: {
  columns: { key: keyof T; label: string; render?: (v: T[keyof T], row: T) => React.ReactNode }[]
  rows: T[]
  onRowClick?: (row: T) => void
}) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
            {columns.map(col => (
              <th key={String(col.key)} style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              onClick={() => onRowClick?.(row)}
              style={{
                borderBottom: '1px solid var(--color-border)',
                cursor: onRowClick ? 'pointer' : 'default',
                transition: 'background 150ms',
              }}
              onMouseEnter={e => { if (onRowClick) e.currentTarget.style.background = 'var(--color-surface-hover)' }}
              onMouseLeave={e => { e.currentTarget.style.background = '' }}
            >
              {columns.map(col => (
                <td key={String(col.key)} style={{ padding: '12px 16px', color: 'var(--color-text)' }}>
                  {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <EmptyState message="データがありません" />}
    </div>
  )
}
```
