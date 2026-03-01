import { Routes, Route } from 'react-router-dom'
import { AuthGuard } from '@common-auth/react'
import Home from './pages/Home'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'

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
    </Routes>
  )
}

export default App
