import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@common-auth/react'
import { t } from '../theme/tokens'

export default function Home() {
  const { login } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loginCalled = useRef(false)

  const startLogin = async () => {
    setError(null)
    setLoading(true)
    try {
      await login()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'ログイン画面へ遷移できませんでした')
      setLoading(false)
    }
  }

  useEffect(() => {
    if (loginCalled.current) return
    loginCalled.current = true
    startLogin()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [login])

  return (
    <div className="container" style={{ paddingTop: '4rem' }}>
      <div
        className="card"
        style={{
          maxWidth: 520,
          margin: '0 auto',
          textAlign: 'center',
          border: `1px solid ${t.border}`,
        }}
      >
        <h1 style={{ marginBottom: '0.75rem' }}>Common Auth</h1>
        <p style={{ color: t.textMuted, marginBottom: '1rem' }}>
          {loading ? 'ログイン画面へ移動中です…' : 'ログインできませんでした。再試行してください。'}
        </p>

        {error && (
          <div
            style={{
              background: '#fee2e2',
              color: '#b91c1c',
              padding: '0.75rem 1rem',
              borderRadius: t.radiusMd,
              marginBottom: '1rem',
              fontSize: '0.875rem',
              textAlign: 'left',
            }}
          >
            <strong>ログインエラー:</strong> {error}
          </div>
        )}

        <button className="btn btn-primary" onClick={startLogin} disabled={loading}>
          {loading ? 'ログイン画面へ移動中...' : 'ログイン画面を開く'}
        </button>
      </div>
    </div>
  )
}
