import { useAuth } from '@common-auth/react'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

export default function Home() {
  const { isAuthenticated, isLoading, login, register, resetPassword } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  if (isLoading) {
    return <div className="loading">Loading...</div>
  }

  if (isAuthenticated) {
    return null
  }

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">🔐 Common Auth</div>
      </nav>

      <div className="container">
        <div className="hero">
          <h1>Secure Authentication Platform</h1>
          <p>
            Portable authentication with Keycloak, OIDC, and PKCE.<br />
            Supports MFA, password reset, and self-registration.
          </p>

          <div className="btn-group" style={{ justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={login}>
              🔑 Login
            </button>
            <button className="btn btn-secondary" onClick={register}>
              ✨ Register
            </button>
          </div>

          <p style={{ marginTop: '1rem' }}>
            <button className="btn btn-link" onClick={resetPassword}>
              Forgot password?
            </button>
          </p>
        </div>

        <div className="features">
          <div className="feature-card">
            <h3>🔐 OIDC + PKCE</h3>
            <p>Secure Authorization Code Flow with Proof Key for Code Exchange</p>
          </div>
          <div className="feature-card">
            <h3>📱 Two-Factor Auth</h3>
            <p>TOTP-based MFA support via authenticator apps</p>
          </div>
          <div className="feature-card">
            <h3>📧 Password Reset</h3>
            <p>Email-based password recovery flow</p>
          </div>
          <div className="feature-card">
            <h3>👤 Self-Registration</h3>
            <p>User registration with email verification</p>
          </div>
        </div>
      </div>
    </div>
  )
}
