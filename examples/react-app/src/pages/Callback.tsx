import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

export default function Callback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const { handleCallback } = useAuth()
  const callbackProcessed = useRef(false)

  useEffect(() => {
    if (callbackProcessed.current) return
    callbackProcessed.current = true

    const processCallback = async () => {
      try {
        await handleCallback()
        navigate('/dashboard', { replace: true })
      } catch (err) {
        console.error('Callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
      }
    }

    processCallback()
  }, [handleCallback, navigate])

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
