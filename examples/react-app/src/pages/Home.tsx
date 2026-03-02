import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@common-auth/react'

export default function Home() {
  const { isAuthenticated, isLoading, login } = useAuth()
  const navigate = useNavigate()
  const loginCalled = useRef(false)

  useEffect(() => {
    if (isLoading) return
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    } else if (!loginCalled.current) {
      loginCalled.current = true
      login()
    }
  }, [isLoading, isAuthenticated, login, navigate])

  return <div className="loading">認証中...</div>
}
