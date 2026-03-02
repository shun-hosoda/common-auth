import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

export default function Dashboard() {
  const { user, logout, configureMFA, getAccessToken, hasRole, openUserManagement } = useAuth()
  const navigate = useNavigate()

  const email = user?.profile?.email || 'Unknown'
  const name = user?.profile?.name || user?.profile?.preferred_username || email
  const initial = name.charAt(0).toUpperCase()

  const isTenantAdmin = hasRole('tenant_admin')
  const isSuperAdmin = hasRole('super_admin')
  const isDev = import.meta.env.DEV

  const handleCopyToken = () => {
    const token = getAccessToken()
    if (token) {
      navigator.clipboard.writeText(token)
      alert('アクセストークンをクリップボードにコピーしました')
    }
  }

  const getRoleBadge = () => {
    if (isSuperAdmin) return { label: 'スーパー管理者', color: '#dc2626' }
    if (isTenantAdmin) return { label: 'テナント管理者', color: '#2563eb' }
    return { label: '一般ユーザー', color: '#16a34a' }
  }

  const badge = getRoleBadge()

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">🔐 Common Auth</div>
        <div className="user-info">
          <span
            style={{
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              background: badge.color,
              color: '#fff',
              fontSize: '0.75rem',
              fontWeight: 600,
              marginRight: '0.5rem',
            }}
          >
            {badge.label}
          </span>
          <span>{email}</span>
          <button className="btn btn-secondary" onClick={logout}>
            ログアウト
          </button>
        </div>
      </nav>

      <div className="container">
        <div className="section">
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="avatar">{initial}</div>
              <div>
                <h2 style={{ margin: 0 }}>ようこそ、{name}!</h2>
                <p style={{ color: 'var(--text-muted)', margin: 0 }}>{email}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="section">
          <h2>アカウント操作</h2>
          <div className="btn-group">
            <button className="btn btn-primary" onClick={configureMFA}>
              📱 MFA設定
            </button>
            {isDev && (
              <button className="btn btn-secondary" onClick={handleCopyToken}>
                🔑 アクセストークンをコピー
              </button>
            )}
            <button className="btn btn-danger" onClick={logout}>
              🚪 ログアウト
            </button>
          </div>
        </div>

        {(isTenantAdmin || isSuperAdmin) && (
          <div className="section">
            <h2>管理操作</h2>
            <div className="btn-group">
              {(isTenantAdmin || isSuperAdmin) && (
                <button
                  className="btn btn-primary"
                  onClick={() => navigate('/admin/users')}
                >
                  👥 ユーザー管理
                </button>
              )}
              {isSuperAdmin && (
                <button
                  className="btn btn-secondary"
                  onClick={openUserManagement}
                >
                  🔧 Keycloak管理コンソール
                </button>
              )}
            </div>
          </div>
        )}

        <div className="section">
          <h2>ユーザープロフィール</h2>
          <div className="card">
            <pre
              style={{
                background: 'var(--bg)',
                padding: '1rem',
                borderRadius: '8px',
                overflow: 'auto',
                fontSize: '0.875rem',
              }}
            >
              {JSON.stringify(user?.profile, null, 2)}
            </pre>
          </div>
        </div>

        <div className="section">
          <h2>トークン情報</h2>
          <div className="card">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>有効期限</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    {user?.expires_at
                      ? new Date(user.expires_at * 1000).toLocaleString('ja-JP')
                      : 'N/A'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>トークン種別</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    {user?.token_type || 'Bearer'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>スコープ</td>
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
