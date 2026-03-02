import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080'
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'common-auth'

export default function AdminUsers() {
  const { user, logout, hasRole, openUserManagement } = useAuth()
  const navigate = useNavigate()

  const isSuperAdmin = hasRole('super_admin')
  const email = user?.profile?.email || 'Unknown'

  const keycloakUsersUrl = `${KEYCLOAK_URL}/admin/${KEYCLOAK_REALM}/console/#/users`

  const handleOpenKeycloak = () => {
    window.open(keycloakUsersUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">🔐 Common Auth</div>
        <div className="user-info">
          <span>{email}</span>
          <button className="btn btn-secondary" onClick={logout}>
            ログアウト
          </button>
        </div>
      </nav>

      <div className="container">
        <div className="section">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/dashboard')}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.875rem' }}
            >
              ← ダッシュボードへ戻る
            </button>
            <h1 style={{ margin: 0 }}>ユーザー管理</h1>
          </div>
        </div>

        <div className="section">
          <div className="card">
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ margin: '0 0 0.5rem 0' }}>Keycloakでユーザーを管理</h2>
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                ユーザーの一覧表示・新規登録・編集・無効化はKeycloak管理コンソールで行います。
                下のボタンから管理画面を開いてください。
              </p>
            </div>

            <div
              style={{
                background: 'var(--bg)',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1.5rem',
                borderLeft: '4px solid #2563eb',
              }}
            >
              <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem' }}>管理コンソールで可能な操作</h3>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-muted)' }}>
                <li>ユーザー一覧の表示・検索</li>
                <li>新規ユーザーの作成</li>
                <li>ユーザー情報の編集（名前・メール・属性）</li>
                <li>パスワードのリセット</li>
                <li>ユーザーの有効化・無効化</li>
                <li>ロールの割り当て・変更</li>
              </ul>
            </div>

            <div className="btn-group">
              <button className="btn btn-primary" onClick={handleOpenKeycloak}>
                👥 Keycloakユーザー管理を開く
              </button>
              {isSuperAdmin && (
                <button className="btn btn-secondary" onClick={openUserManagement}>
                  🔧 Keycloak管理コンソール（フル）
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="section">
          <div className="card">
            <h3 style={{ margin: '0 0 0.75rem 0' }}>接続情報</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500, width: '140px' }}>Keycloak URL</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    <code>{KEYCLOAK_URL}</code>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>Realm</td>
                  <td style={{ padding: '0.5rem 0', color: 'var(--text-muted)' }}>
                    <code>{KEYCLOAK_REALM}</code>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '0.5rem 0', fontWeight: 500 }}>管理コンソール</td>
                  <td style={{ padding: '0.5rem 0' }}>
                    <a
                      href={keycloakUsersUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#2563eb', wordBreak: 'break-all' }}
                    >
                      {keycloakUsersUrl}
                    </a>
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
