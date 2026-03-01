# @common-auth/react

common-auth認証プラットフォーム用のReact Hooks SDK

## インストール

```bash
npm install @common-auth/react
```

## クイックスタート

```tsx
import { AuthProvider, useAuth, AuthGuard } from '@common-auth/react';

function App() {
  return (
    <AuthProvider
      authority="http://localhost:8080/realms/common-auth"
      clientId="frontend-app"
      redirectUri="http://localhost:3000/callback"
      postLogoutRedirectUri="http://localhost:3000"
    >
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/callback" element={<Callback />} />
          <Route path="/dashboard" element={
            <AuthGuard>
              <Dashboard />
            </AuthGuard>
          } />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
```

## API

### AuthProvider

アプリを `AuthProvider` でラップして認証を有効化します。

```tsx
<AuthProvider
  authority="http://localhost:8080/realms/common-auth"
  clientId="frontend-app"
  redirectUri="http://localhost:3000/callback"
  postLogoutRedirectUri="http://localhost:3000"  // オプション
  scope="openid profile email"                   // オプション
  automaticSilentRenew={true}                    // オプション
>
  {children}
</AuthProvider>
```

### useAuth

認証状態とメソッドにアクセスします。

```tsx
function Dashboard() {
  const {
    user,              // OIDCユーザーオブジェクト
    isAuthenticated,   // boolean
    isLoading,         // boolean
    error,             // Error | null
    login,             // () => Promise<void>
    logout,            // () => Promise<void>
    register,          // () => void - Keycloak登録画面へリダイレクト
    resetPassword,     // () => void - パスワードリセット画面へリダイレクト
    configureMFA,      // () => void - MFA設定画面へリダイレクト
    handleCallback,    // () => Promise<void> - OIDCコールバック処理
    getAccessToken,    // () => string | null
  } = useAuth();

  return (
    <div>
      <p>ようこそ、{user?.profile.email}</p>
      <button onClick={logout}>ログアウト</button>
      <button onClick={configureMFA}>MFA設定</button>
    </div>
  );
}
```

### AuthGuard

未認証ユーザーからルートを保護します。

```tsx
// デフォルト: ログインにリダイレクト
<AuthGuard>
  <ProtectedContent />
</AuthGuard>

// カスタムローディング状態
<AuthGuard fallback={<Spinner />}>
  <ProtectedContent />
</AuthGuard>

// カスタムリダイレクトハンドラー（例: Next.js）
<AuthGuard onUnauthenticated={() => router.push('/login')}>
  <ProtectedContent />
</AuthGuard>
```

## コールバックの処理

OIDCリダイレクトを処理するコールバックページを作成：

```tsx
// pages/callback.tsx
import { useEffect } from 'react';
import { useAuth } from '@common-auth/react';

export default function Callback() {
  const { handleCallback } = useAuth();

  useEffect(() => {
    handleCallback()
      .then(() => window.location.href = '/dashboard')
      .catch(console.error);
  }, [handleCallback]);

  return <div>ログイン処理中...</div>;
}
```

**重要**: 常に `useAuth().handleCallback()` を使用してください。別の `UserManager` インスタンスを作成しないでください。これによりアプリケーション全体で一貫したトークン管理が保証されます。

## 要件

- React 18+
- KeycloakまたはOIDC準拠のIdP

## ライセンス

MIT
