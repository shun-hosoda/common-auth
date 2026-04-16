import { useEffect, useState } from 'react'
import { useAuth } from '@common-auth/react'
import { type MfaStatus, getMfaStatus } from '../api/adminApi'
import { t } from '../theme/tokens'
import { MdLockOpen, MdWarning, MdCheckCircle } from 'react-icons/md'
import type { ReactNode } from 'react'

/**
 * MfaStatusCard — displays the user's MFA status on the Dashboard.
 *
 * 3 states:
 *  1. mfa_enabled=false          → grey  "MFA 無効"
 *  2. mfa_enabled=true, !configured → amber "MFA 要設定"
 *  3. mfa_enabled=true, configured  → green "MFA 有効"
 */
export default function MfaStatusCard() {
  const { getAccessToken } = useAuth()
  const [status, setStatus] = useState<MfaStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const token = getAccessToken()
      if (!token) { setLoading(false); return }
      try {
        const data = await getMfaStatus(token)
        if (!cancelled) setStatus(data)
      } catch {
        // Silently ignore — card just won't render content
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <div style={{
        background: t.surface, border: `1px solid ${t.border}`,
        borderRadius: t.radiusLg, padding: '16px', boxShadow: t.shadowSm,
      }}>
        <div style={{ color: t.textMuted, fontSize: '0.85rem' }}>MFA ステータス読み込み中...</div>
      </div>
    )
  }

  if (!status) return null

  // Determine visual state
  let icon: ReactNode
  let label: string
  let description: string
  let bgColor: string
  let textColor: string
  let borderColor: string

  if (!status.mfa_enabled) {
    icon = <MdLockOpen />
    label = 'MFA 無効'
    description = 'テナントでMFAは有効化されていません'
    bgColor = '#f8fafc'
    textColor = t.textMuted
    borderColor = t.border
  } else if (!status.mfa_configured) {
    icon = <MdWarning />
    label = 'MFA 要設定'
    description = 'MFAが有効ですが、まだ設定が完了していません。次回ログイン時に設定を求められます。'
    bgColor = '#fffbeb'
    textColor = '#92400e'
    borderColor = '#fbbf24'
  } else {
    icon = <MdCheckCircle />
    label = 'MFA 有効'
    description = `${status.mfa_method === 'totp' ? 'TOTP（認証アプリ）' : status.mfa_method}で保護されています`
    bgColor = '#f0fdf4'
    textColor = '#15803d'
    borderColor = '#4ade80'
  }

  return (
    <div style={{
      background: bgColor,
      border: `1px solid ${borderColor}`,
      borderRadius: t.radiusLg,
      padding: '16px 20px',
      boxShadow: t.shadowSm,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
        <span style={{ fontSize: '1.2rem' }} aria-hidden="true">{icon}</span>
        <span style={{ fontWeight: 600, fontSize: '0.95rem', color: textColor }}>{label}</span>
      </div>
      <div style={{ fontSize: '0.8rem', color: textColor, lineHeight: 1.5 }}>
        {description}
      </div>
    </div>
  )
}
