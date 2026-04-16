import { useEffect, useRef, useState } from 'react'
import { MdKey, MdVisibility, MdVisibilityOff } from 'react-icons/md'
import { changePasswordApi, ChangePasswordError } from '../api/accountApi'
import { t } from '../theme/tokens'

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ChangePasswordModalProps {
  open: boolean
  token: string
  onClose: () => void
  onSuccess: () => void
}

// ── State machine ─────────────────────────────────────────────────────────────

type ModalState = 'IDLE' | 'SUBMITTING' | 'ERROR'

// ── Sub-components ────────────────────────────────────────────────────────────

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  show: boolean
  disabled: boolean
  autoComplete?: string
  onChange: (v: string) => void
  onToggleShow: () => void
}

function PasswordField({
  id,
  label,
  value,
  show,
  disabled,
  autoComplete = 'off',
  onChange,
  onToggleShow,
}: PasswordFieldProps) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <label
        htmlFor={id}
        style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: t.text, marginBottom: '6px' }}
      >
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        <input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          disabled={disabled}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
          style={{
            width: '100%',
            padding: '10px 44px 10px 12px',
            border: `1px solid ${t.border}`,
            borderRadius: t.radiusMd,
            fontSize: '0.9rem',
            color: t.text,
            background: disabled ? '#f1f5f9' : '#fff',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        <button
          type="button"
          disabled={disabled}
          onClick={onToggleShow}
          aria-label={show ? 'パスワードを隠す' : 'パスワードを表示する'}
          style={{
            position: 'absolute',
            right: '10px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: disabled ? 'default' : 'pointer',
            fontSize: '1rem',
            padding: '4px',
            color: t.textMuted,
            lineHeight: 1,
          }}
        >
          {show ? <MdVisibilityOff /> : <MdVisibility />}
        </button>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function ChangePasswordModal({ open, token, onClose, onSuccess }: ChangePasswordModalProps) {
  const [state, setState] = useState<ModalState>('IDLE')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  const firstInputRef = useRef<HTMLInputElement>(null)
  const isSubmitting = state === 'SUBMITTING'

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setState('IDLE')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setShowCurrent(false)
      setShowNew(false)
      setShowConfirm(false)
      setErrorMsg(null)
      setValidationError(null)
      // Focus first input after render
      setTimeout(() => firstInputRef.current?.focus(), 50)
    }
  }, [open])

  // Close on Escape key
  useEffect(() => {
    if (!open || isSubmitting) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, isSubmitting, onClose])

  if (!open) return null

  const validate = (): boolean => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setValidationError('すべての項目を入力してください')
      return false
    }
    if (newPassword !== confirmPassword) {
      setValidationError('新しいパスワードと確認用パスワードが一致しません')
      return false
    }
    if (newPassword.length < 8) {
      setValidationError('新しいパスワードは8文字以上で入力してください')
      return false
    }
    setValidationError(null)
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setState('SUBMITTING')
    setErrorMsg(null)
    try {
      await changePasswordApi(token, currentPassword, newPassword)
      // Success: notify parent, let parent close the modal
      onSuccess()
    } catch (err) {
      setState('ERROR')
      if (err instanceof ChangePasswordError) {
        setErrorMsg(err.message)
      } else {
        setErrorMsg('予期しないエラーが発生しました')
      }
      // Clear only the current password field on failure
      setCurrentPassword('')
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        role="presentation"
        onClick={isSubmitting ? undefined : onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.45)',
          zIndex: 1000,
        }}
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-pw-title"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1001,
          width: 'min(480px, 92vw)',
          background: t.surface,
          borderRadius: t.radiusLg,
          boxShadow: '0 20px 60px 0 rgb(0 0 0 / 0.25)',
          padding: '28px 28px 24px',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2
            id="change-pw-title"
            style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: t.text }}
          >
            <MdKey style={{ verticalAlign: 'middle', marginRight: 4 }} /> パスワードを変更
          </h2>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            aria-label="閉じる"
            style={{
              background: 'none',
              border: 'none',
              cursor: isSubmitting ? 'default' : 'pointer',
              fontSize: '1.25rem',
              color: t.textMuted,
              padding: '4px 6px',
              borderRadius: t.radiusMd,
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Error banner */}
        {(errorMsg || validationError) && (
          <div
            role="alert"
            style={{
              background: '#fee2e2',
              color: '#b91c1c',
              padding: '10px 14px',
              borderRadius: t.radiusMd,
              marginBottom: '16px',
              fontSize: '0.875rem',
              lineHeight: 1.5,
            }}
          >
            {validationError ?? errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate>
          <div>
            {/* Attach ref via callback to the underlying <input> */}
            <div style={{ marginBottom: '16px' }}>
              <label
                htmlFor="current-password"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: t.text, marginBottom: '6px' }}
              >
                現在のパスワード
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  ref={firstInputRef}
                  id="current-password"
                  type={showCurrent ? 'text' : 'password'}
                  value={currentPassword}
                  disabled={isSubmitting}
                  autoComplete="current-password"
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 44px 10px 12px',
                    border: `1px solid ${t.border}`,
                    borderRadius: t.radiusMd,
                    fontSize: '0.9rem',
                    color: t.text,
                    background: isSubmitting ? '#f1f5f9' : '#fff',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => setShowCurrent((v) => !v)}
                  aria-label={showCurrent ? 'パスワードを隠す' : 'パスワードを表示する'}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: isSubmitting ? 'default' : 'pointer',
                    fontSize: '1rem',
                    padding: '4px',
                    color: t.textMuted,
                    lineHeight: 1,
                  }}
                >
                  {showCurrent ? <MdVisibilityOff /> : <MdVisibility />}
                </button>
              </div>
            </div>
          </div>

          <PasswordField
            id="new-password"
            label="新しいパスワード"
            value={newPassword}
            show={showNew}
            disabled={isSubmitting}
            autoComplete="new-password"
            onChange={setNewPassword}
            onToggleShow={() => setShowNew((v) => !v)}
          />

          <PasswordField
            id="confirm-password"
            label="新しいパスワード（確認）"
            value={confirmPassword}
            show={showConfirm}
            disabled={isSubmitting}
            autoComplete="new-password"
            onChange={setConfirmPassword}
            onToggleShow={() => setShowConfirm((v) => !v)}
          />

          {/* Actions */}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button
              type="button"
              disabled={isSubmitting}
              onClick={onClose}
              style={{
                padding: '10px 20px',
                borderRadius: t.radiusMd,
                border: `1px solid ${t.border}`,
                background: t.surface,
                color: t.text,
                fontWeight: 600,
                cursor: isSubmitting ? 'default' : 'pointer',
                fontSize: '0.9rem',
              }}
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: '10px 20px',
                borderRadius: t.radiusMd,
                border: 'none',
                background: isSubmitting ? '#93c5fd' : t.primary,
                color: t.textInverse,
                fontWeight: 600,
                cursor: isSubmitting ? 'default' : 'pointer',
                fontSize: '0.9rem',
                minWidth: '120px',
              }}
            >
              {isSubmitting ? '変更中...' : 'パスワードを変更'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
