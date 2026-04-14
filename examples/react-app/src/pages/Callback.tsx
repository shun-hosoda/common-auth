import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

export default function Callback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [tabClosed, setTabClosed] = useState(false)
  const { handleCallback } = useAuth()
  const callbackProcessed = useRef(false)

  useEffect(() => {
    if (callbackProcessed.current) return
    callbackProcessed.current = true

    const processCallback = async () => {
      try {
        const state = await handleCallback()

        // 別タブで開いた MFA 設定フローの場合:
        // BroadcastChannel で元タブに完了通知を送り、このタブを閉じる。
        if (state?.broadcastCompletion) {
          try {
            const bc = new BroadcastChannel(state.broadcastCompletion)
            bc.postMessage({ type: 'completed' })
            bc.close()
          } catch {
            // BroadcastChannel 非対応環境でも続行
          }
          // タブを閉じる（opener が null など閉じられない場合もある）
          window.close()
          // 閉じられなかった場合は完了メッセージを表示
          setTabClosed(true)
          return
        }

        // configureMFA / changePassword が state: { returnTo } を渡している場合、
        // アクション完了後にその元ページへ復帰する。
        const returnTo = state?.returnTo
        navigate(returnTo || '/dashboard', { replace: true })
      } catch (err) {
        console.error('Callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
      }
    }

    processCallback()
  }, [handleCallback, navigate])

  if (tabClosed) {
    return (
      <div className="container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <div className="card">
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>✅</div>
          <h2>MFA設定が完了しました</h2>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            このタブを閉じて元の画面に戻ってください。
          </p>
          <button
            className="btn btn-primary"
            style={{ marginTop: '1rem' }}
            onClick={() => window.close()}
          >
            このタブを閉じる
          </button>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <div className="card">
          <h2>Authentication Error</h2>
          <p style={{ color: 'var(--danger)', marginTop: '1rem' }}>{error}</p>
          <button 
            className="btn btn-primary" 
            style={{ marginTop: '1rem' }}
            onClick={() => navigate('/')}
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="loading">
      <div style={{ textAlign: 'center' }}>
        <p>Processing authentication...</p>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Please wait while we complete your login.
        </p>
      </div>
    </div>
  )
}

