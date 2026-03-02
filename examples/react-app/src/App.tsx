import { Routes, Route } from 'react-router-dom'
import { AuthGuard } from '@common-auth/react'
import Home from './pages/Home'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import AdminUsers from './pages/AdminUsers'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/callback" element={<Callback />} />
      <Route path="/dashboard" element={
        <AuthGuard fallback={<div className="loading">Loading...</div>}>
          <Dashboard />
        </AuthGuard>
      } />
      <Route path="/admin/users" element={
        <AuthGuard
          fallback={<div className="loading">Loading...</div>}
          requiredRoles={['tenant_admin', 'super_admin']}
          unauthorizedFallback={
            <div className="container">
              <div className="section">
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                  <h2>アクセス権限がありません</h2>
                  <p style={{ color: 'var(--text-muted)' }}>この画面を表示するにはtenant_admin以上の権限が必要です。</p>
                </div>
              </div>
            </div>
          }
        >
          <AdminUsers />
        </AuthGuard>
      } />
    </Routes>
  )
}

export default App
