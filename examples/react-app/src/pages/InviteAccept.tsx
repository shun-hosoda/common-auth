/**
 * InviteAccept ページ (/invite/accept?token=xxx)
 *
 * 招待リンクを受け取ったユーザーが新規アカウントを作成するパブリックページ。
 * AuthGuard は不要（ログイン不要で表示可能）。
 *
 * セキュリティ:
 *   - URL のトークンがリファラーで漏れるのを防ぐため、
 *     <meta name="referrer" content="no-referrer"> をマウント時に動的設定する (S-1)
 *   - バックエンドからのパスワードポリシーヒントを表示する (S-8)
 *   - 完了後に mfa_required フラグを表示する (S-7)
 */

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  type InvitationAcceptResponse,
  type InvitationValidateResponse,
  acceptInvitation,
  validateInvitationToken,
} from '../api/adminApi'
import { t } from '../theme/tokens'
import { MdLinkOff, MdCheckCircle, MdSearch, MdEmail, MdSecurity, MdVisibility, MdVisibilityOff } from 'react-icons/md'

// ─── Referrer meta (S-1) ──────────────────────────────────────────────────────

function useNoReferrer() {
  useEffect(() => {
    let meta = document.querySelector<HTMLMetaElement>('meta[name="referrer"]')
    const created = !meta
    if (!meta) {
      meta = document.createElement('meta')
      meta.name = 'referrer'
      document.head.appendChild(meta)
    }
    meta.content = 'no-referrer'
    return () => {
      if (created && meta) meta.remove()
    }
  }, [])
}

// ─── Input styles ─────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.875rem',
  fontWeight: 600,
  color: t.text,
  marginBottom: 6,
}

const inputStyle: React.CSSProperties = {
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

// ─── Card wrapper ─────────────────────────────────────────────────────────────

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: t.bg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: t.radiusLg,
          padding: '2.5rem',
          width: '100%',
          maxWidth: 440,
          boxShadow: t.shadowMd,
        }}
      >
        {children}
      </div>
    </div>
  )
}

// ─── Error screen ─────────────────────────────────────────────────────────────

function ErrorScreen({ message }: { message: string }) {
  return (
    <CenteredCard>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: 16 }}><MdLinkOff /></div>
        <h2 style={{ color: t.text, marginTop: 0, marginBottom: 8 }}>
          招待リンクが無効です
        </h2>
        <p style={{ color: t.textMuted, lineHeight: 1.6 }}>{message}</p>
        <p style={{ color: t.textMuted, fontSize: '0.8rem', lineHeight: 1.5 }}>
          問題が解決しない場合は、招待を送った担当者または
          システム管理者にお問い合わせください。
        </p>
      </div>
    </CenteredCard>
  )
}

// ─── Success screen ───────────────────────────────────────────────────────────

function SuccessScreen({ result }: { result: InvitationAcceptResponse }) {
  return (
    <CenteredCard>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', marginBottom: 16 }}><MdCheckCircle /></div>
        <h2 style={{ color: t.text, marginTop: 0, marginBottom: 8 }}>
          アカウントが作成されました
        </h2>
        <p style={{ color: t.textMuted, lineHeight: 1.6 }}>
          アカウントの登録が完了しました。
        </p>

        {result.mfa_required && (
          <div
            style={{
              background: '#eff6ff',
              border: `1px solid #bfdbfe`,
              borderRadius: t.radiusMd,
              padding: '0.875rem 1rem',
              marginTop: '1.25rem',
              textAlign: 'left',
            }}
          >
            <div style={{ fontWeight: 700, color: '#1d4ed8', marginBottom: 4 }}>
              <MdSecurity style={{ verticalAlign: 'middle', marginRight: 4 }} /> 多要素認証の設定が必要です
            </div>
            <p style={{ color: '#1d4ed8', fontSize: '0.875rem', margin: 0, lineHeight: 1.5 }}>
              このテナントでは多要素認証（MFA）が必須です。
              <br />
              ログイン時に認証アプリ（Google Authenticator 等）の設定を求められます。
            </p>
          </div>
        )}

        <a
          href="/"
          style={{
            display: 'inline-block',
            marginTop: '1.5rem',
            padding: '10px 28px',
            background: t.primary,
            color: '#fff',
            borderRadius: t.radiusMd,
            fontWeight: 600,
            textDecoration: 'none',
            fontSize: '0.95rem',
          }}
        >
          ログインページへ
        </a>
      </div>
    </CenteredCard>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function InviteAccept() {
  useNoReferrer()

  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [validateResult, setValidateResult] = useState<InvitationValidateResponse | null>(null)
  const [validateError, setValidateError] = useState<string | null>(null)
  const [validating, setValidating] = useState(true)

  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [acceptResult, setAcceptResult] = useState<InvitationAcceptResponse | null>(null)

  const displayNameRef = useRef<HTMLInputElement>(null)

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setValidateError('招待トークンが指定されていません。')
      setValidating(false)
      return
    }
    validateInvitationToken(token)
      .then((res) => {
        setValidateResult(res)
        // フォーカス to display name
        setTimeout(() => displayNameRef.current?.focus(), 50)
      })
      .catch(() => {
        setValidateError('この招待リンクは無効か、期限が切れています。')
      })
      .finally(() => setValidating(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== passwordConfirm) {
      setSubmitError('パスワードが一致しません。')
      return
    }
    if (password.length < 8) {
      setSubmitError('パスワードは8文字以上で入力してください。')
      return
    }
    setSubmitError(null)
    setSubmitting(true)
    try {
      const result = await acceptInvitation({ token, display_name: displayName.trim(), password })
      setAcceptResult(result)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '登録に失敗しました'
      // バックエンドは "invitation_not_found" / "already_accepted" 等を返す
      if (msg.includes('already_accepted')) {
        setSubmitError('この招待は既に使用されています。')
      } else if (msg.includes('invitation_not_found') || msg.includes('404')) {
        setSubmitError('招待リンクが無効です。再度ご確認ください。')
      } else if (msg.includes('password')) {
        setSubmitError('パスワードがポリシーを満たしていません。')
      } else {
        setSubmitError(msg)
      }
    } finally {
      setSubmitting(false)
    }
  }

  // ──── Render states ────

  if (validating) {
    return (
      <CenteredCard>
        <div style={{ textAlign: 'center', color: t.textMuted }}>
          <div style={{ fontSize: '2rem', marginBottom: 12 }}><MdSearch /></div>
          <p>招待リンクを確認しています...</p>
        </div>
      </CenteredCard>
    )
  }

  if (validateError || !validateResult) {
    return <ErrorScreen message={validateError ?? '招待リンクの検証に失敗しました。'} />
  }

  if (acceptResult) {
    return <SuccessScreen result={acceptResult} />
  }

  const v = validateResult
  const roleName = v.role === 'tenant_admin' ? 'テナント管理者' : '一般ユーザー'

  return (
    <CenteredCard>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
          <div style={{ fontSize: '2.5rem' }}><MdEmail /></div>
        </div>
        <h1
          style={{
            fontSize: '1.4rem',
            fontWeight: 700,
            color: t.text,
            margin: '0 0 8px',
            textAlign: 'center',
          }}
        >
          {v.tenant_display_name} に招待されました
        </h1>
        {v.inviter_display_name && (
          <p
            style={{
              fontSize: '0.875rem',
              color: t.textMuted,
              textAlign: 'center',
              margin: '0 0 4px',
            }}
          >
            {v.inviter_display_name} さんから招待が届いています
          </p>
        )}
        <p
          style={{
            fontSize: '0.875rem',
            color: t.textMuted,
            textAlign: 'center',
            margin: 0,
          }}
        >
          メールアドレス: <strong style={{ color: t.text }}>{v.email}</strong>&nbsp;/&nbsp;
          権限: <strong style={{ color: t.text }}>{roleName}</strong>
        </p>
      </div>

      {/* Custom message */}
      {v.custom_message && (
        <div
          style={{
            background: t.bg,
            border: `1px solid ${t.border}`,
            borderRadius: t.radiusMd,
            padding: '0.875rem 1rem',
            marginBottom: '1.5rem',
            fontSize: '0.875rem',
            color: t.textMuted,
            lineHeight: 1.6,
            fontStyle: 'italic',
          }}
        >
          "{v.custom_message}"
        </div>
      )}

      {/* Error banner */}
      {submitError && (
        <div
          style={{
            background: '#fef2f2',
            border: `1px solid #fecaca`,
            borderRadius: t.radiusMd,
            padding: '0.75rem 1rem',
            color: t.danger,
            marginBottom: '1rem',
            fontSize: '0.875rem',
          }}
        >
          {submitError}
        </div>
      )}

      {/* Registration form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Display name */}
        <div>
          <label style={labelStyle} htmlFor="display-name">
            表示名 *
          </label>
          <input
            ref={displayNameRef}
            id="display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="例: 山田 太郎"
            required
            maxLength={200}
            style={inputStyle}
            autoComplete="name"
          />
        </div>

        {/* Password */}
        <div>
          <label style={labelStyle} htmlFor="password">
            パスワード *
          </label>
          <div style={{ position: 'relative' }}>
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="8文字以上"
              required
              minLength={8}
              style={{ ...inputStyle, paddingRight: 44 }}
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'パスワードを非表示' : 'パスワードを表示'}
              style={{
                position: 'absolute',
                right: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 4,
                fontSize: '0.9rem',
                color: t.textMuted,
              }}
            >
              {showPassword ? <MdVisibilityOff /> : <MdVisibility />}
            </button>
          </div>
          {/* Password policy hint (S-8) */}
          {v.password_policy_hint && (
            <p style={{ fontSize: '0.75rem', color: t.textMuted, marginTop: 4 }}>
              💡 {v.password_policy_hint}
            </p>
          )}
        </div>

        {/* Password confirm */}
        <div>
          <label style={labelStyle} htmlFor="password-confirm">
            パスワード（確認）*
          </label>
          <input
            id="password-confirm"
            type={showPassword ? 'text' : 'password'}
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="同じパスワードを再入力"
            required
            minLength={8}
            style={{
              ...inputStyle,
              border: passwordConfirm && password !== passwordConfirm
                ? `1.5px solid ${t.danger}`
                : inputStyle.border,
            }}
            autoComplete="new-password"
          />
          {passwordConfirm && password !== passwordConfirm && (
            <p style={{ fontSize: '0.75rem', color: t.danger, marginTop: 4 }}>
              パスワードが一致しません
            </p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting || !displayName.trim() || !password || password !== passwordConfirm}
          style={{
            width: '100%',
            padding: '12px',
            background:
              submitting || !displayName.trim() || !password || password !== passwordConfirm
                ? '#93c5fd'
                : t.primary,
            color: '#fff',
            border: 'none',
            borderRadius: t.radiusMd,
            fontWeight: 700,
            fontSize: '1rem',
            cursor:
              submitting || !displayName.trim() || !password || password !== passwordConfirm
                ? 'not-allowed'
                : 'pointer',
            marginTop: 4,
          }}
        >
          {submitting ? '処理中...' : 'アカウントを作成する'}
        </button>
      </form>

      <p
        style={{
          fontSize: '0.75rem',
          color: t.textMuted,
          textAlign: 'center',
          marginTop: '1.25rem',
          lineHeight: 1.5,
        }}
      >
        このリンクには有効期限があります。問題が発生した場合は、
        招待を送った担当者にお問い合わせください。
      </p>
    </CenteredCard>
  )
}
