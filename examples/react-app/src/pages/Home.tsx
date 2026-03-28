import { useEffect, useRef } from 'react'
import { useAuth } from '@common-auth/react'

export default function Home() {
  const { login } = useAuth()
  const loginCalled = useRef(false)

  useEffect(() => {
    // /（ログインページ）に到達したら常に login() を呼ぶ。
    // login() は prompt=login を渡すため、localStorage に有効なトークンが残っていても
    // Keycloak は必ず再認証（パスワード + MFA）を要求する。
    // isAuthenticated チェックによる「ダッシュボードへのショートカット」は
    // MFA ゲートを回避してしまうため使用しない。
    if (!loginCalled.current) {
      loginCalled.current = true
      login()
    }
  }, [login])

  return <div className="loading">認証中...</div>
}
