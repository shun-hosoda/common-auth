import { useAuth } from '@common-auth/react'

export default function Dashboard() {
  const { user, logout, configureMFA, getAccessToken } = useAuth()

  const email = user?.profile?.email || 'Unknown'
  const name = user?.profile?.name || user?.profile?.preferred_username || email
  const initial = name.charAt(0).toUpperCase()

  const handleCopyToken = () => {
    const token = getAccessToken()
    if (token) {
      navigator.clipboard.writeText(token)
      alert('Access token copied to clipboard!')
    }
  }

  const isDev = import.meta.env.DEV

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">🔐 Common Auth</div>
        <div className="user-info">
          <span>{email}</span>
          <button className="btn btn-secondary" onClick={logout}>
            Logout
          </button>
        </div>
      </nav>

      <div className="container">
        <div className="section">
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="avatar">{initial}</div>
              <div>
                <h2 style={{ margin: 0 }}>Welcome, {name}!</h2>
                <p style={{ color: 'var(--text-muted)', margin: 0 }}>{email}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="section">
          <h2>Account Actions</h2>
          <div className="btn-group">
            <button className="btn btn-primary" onClick={configureMFA}>
              📱 Setup MFA
            </button>
            {isDev && (
              <button className="btn btn-secondary" onClick={handleCopyToken}>
                🔑 Copy Access Token
              </button>
            )}
            <button className="btn btn-danger" onClick={logout}>
              🚪 Logout
            </button>
          </div>
        </div>

        <div className="section">
          <h2>User Profile</h2>
          <div className="card">
            <pre style={{ 
              background: 'var(--bg)', 
              padding: '1rem', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.875rem'
            }}>
              {JSON.stringify(user?.profile, null, 2)}
            </pre>
          </div>
        </div>

        <div className="section">
          <h2>Token Info</h2>
          <div className="card">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>Token Expires</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    {user?.expires_at 
                      ? new Date(user.expires_at * 1000).toLocaleString() 
                      : 'N/A'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>Token Type</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    {user?.token_type || 'Bearer'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>Scopes</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    {user?.scope || 'openid profile email'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
