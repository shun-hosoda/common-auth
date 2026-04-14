import { Routes, Route } from 'react-router-dom'
import { AuthGuard } from '@common-auth/react'
import Home from './pages/Home'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import AdminUsers from './pages/AdminUsers'
import AdminClients from './pages/AdminClients'
import SecuritySettings from './pages/SecuritySettings'
import PersonalSecuritySettings from './pages/PersonalSecuritySettings'
import AdminInvitations from './pages/AdminInvitations'
import InviteAccept from './pages/InviteAccept'
import MfaSetupRedirect from './pages/MfaSetupRedirect'

const ADMIN_UNAUTHORIZED = (
  <div className="container">
    <div className="section">
      <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
        <h2>アクセス権限がありません</h2>
        <p style={{ color: 'var(--text-muted)' }}>この画面を表示するにはtenant_admin以上の権限が必要です。</p>
      </div>
    </div>
  </div>
)

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/callback" element={<Callback />} />

      {/* Public invitation accept page — NO AuthGuard */}
      <Route path="/invite/accept" element={<InviteAccept />} />

      <Route path="/dashboard" element={
        <AuthGuard fallback={<div className="loading">Loading...</div>}>
          <Dashboard />
        </AuthGuard>
      } />
      <Route path="/admin/users" element={
        <AuthGuard
          fallback={<div className="loading">Loading...</div>}
          requiredRoles={['tenant_admin', 'super_admin']}
          unauthorizedFallback={ADMIN_UNAUTHORIZED}
        >
          <AdminUsers />
        </AuthGuard>
      } />
      <Route path="/admin/invitations" element={
        <AuthGuard
          fallback={<div className="loading">Loading...</div>}
          requiredRoles={['tenant_admin', 'super_admin']}
          unauthorizedFallback={ADMIN_UNAUTHORIZED}
        >
          <AdminInvitations />
        </AuthGuard>
      } />
      <Route path="/security" element={
        <AuthGuard
          fallback={<div className="loading">Loading...</div>}
          requiredRoles={['tenant_admin', 'super_admin']}
          unauthorizedFallback={ADMIN_UNAUTHORIZED}
        >
          <SecuritySettings />
        </AuthGuard>
      } />
      <Route path="/me/security" element={
        <AuthGuard fallback={<div className="loading">Loading...</div>}>
          <PersonalSecuritySettings />
        </AuthGuard>
      } />
      <Route path="/admin/clients" element={
        <AuthGuard
          fallback={<div className="loading">Loading...</div>}
          requiredRoles={['super_admin']}
          unauthorizedFallback={
            <div className="container">
              <div className="section">
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                  <h2>アクセス権限がありません</h2>
                  <p style={{ color: 'var(--text-muted)' }}>この画面を表示するにはsuper_adminの権限が必要です。</p>
                </div>
              </div>
            </div>
          }
        >
          <AdminClients />
        </AuthGuard>
      } />
      {/* MFA setup redirect page — opened in a new tab */}
      <Route path="/me/mfa-setup" element={
        <AuthGuard fallback={<div className="loading">Loading...</div>}>
          <MfaSetupRedirect />
        </AuthGuard>
      } />
    </Routes>
  )
}

export default App
