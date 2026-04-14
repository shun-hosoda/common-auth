import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@common-auth/react'
import { t } from '../theme/tokens'

/**
 * 別タブで開かれる MFA 設定開始ページ。
 *
 * PersonalSecuritySettings が window.open('/auth/mfa-setup', '_blank') で
 * このページを別タブで起動する。
 * ページが表示されたら自動的に configureMFA を呼び出し、
 * Keycloak の CONFIGURE_TOTP アクション画面へリダイレクトする。
 *
 * 設定完了後にコールバックが処理されると Callback.tsx が
 *   state.broadcastCompletion = 'mfa-configured'
 * を検知して BroadcastChannel で元タブへ通知し、このタブを閉じる。
 */
const BROADCAST_CHANNEL = 'mfa-configured'

export default function MfaSetupRedirect() {
  const { configureMFA, isLoading, isAuthenticated } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    // 認証状態の読み込みが完了するまで待機
    if (isLoading) return
    if (!isAuthenticated) {
      setError('ログインが必要です。このタブを閉じて再度お試しください。')
      return
    }
    // React StrictMode の二重実行対策
    if (started.current) return
    started.current = true

    configureMFA({ broadcastCompletion: BROADCAST_CHANNEL }).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : 'MFA設定の開始に失敗しました')
    })
  }, [isLoading, isAuthenticated, configureMFA])

  if (error) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: t.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}>
        <div style={{
          background: t.surface, border: `1px solid ${t.border}`,
          borderRadius: t.radiusLg, padding: '32px 40px', textAlign: 'center',
          boxShadow: t.shadowMd, maxWidth: 400,
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⚠️</div>
          <h2 style={{ margin: '0 0 8px', color: t.text, fontSize: '1.1rem' }}>エラーが発生しました</h2>
          <p style={{ margin: '0 0 20px', color: t.textMuted, fontSize: '0.875rem' }}>{error}</p>
          <button
            onClick={() => window.close()}
            style={{
              padding: '10px 24px', borderRadius: t.radiusMd,
              background: t.primary, color: t.textInverse,
              border: 'none', cursor: 'pointer', fontWeight: 600,
            }}
          >
            閉じる
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: t.bg, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      <div style={{
        background: t.surface, border: `1px solid ${t.border}`,
        borderRadius: t.radiusLg, padding: '32px 40px', textAlign: 'center',
        boxShadow: t.shadowMd, maxWidth: 400,
      }}>
        <div style={{ fontSize: '2rem', marginBottom: '12px' }}>🔐</div>
        <h2 style={{ margin: '0 0 8px', color: t.text, fontSize: '1.1rem' }}>MFA設定画面へ移動中</h2>
        <p style={{ margin: '0', color: t.textMuted, fontSize: '0.875rem' }}>
          Keycloak の認証画面に遷移しています。しばらくお待ちください...
        </p>
        <div style={{
          marginTop: '20px', height: 4, borderRadius: 2,
          background: t.border, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: '40%', background: t.primary,
            borderRadius: 2, animation: 'mfa-slide 1.2s ease-in-out infinite',
          }} />
        </div>
        <style>{`
          @keyframes mfa-slide {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
          }
        `}</style>
      </div>
    </div>
  )
}
