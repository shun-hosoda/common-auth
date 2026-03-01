# ADR-008: Frontend SDK技術選定

## ステータス

承認

## コンテキスト

Phase 2bでFrontend SDK（React Hooks）を実装する必要がある（FR-005）。このSDKは以下の機能を提供する:
- ログイン/ログアウト
- ユーザー情報取得
- 認証状態管理
- ルートガード（未認証ユーザーのリダイレクト）
- Phase 2追加機能: ユーザー登録、パスワードリセット、MFA設定

### 要件
- React 18+対応
- TypeScript型安全性
- OIDC Authorization Code Flow + PKCE準拠
- Keycloak（IdP）に依存しない設計（将来的な移行を考慮）
- npm パッケージとして配布（`@common-auth/react`）
- 開発者に優しいAPI（React Hooks）

## 決定

**`oidc-client-ts` + 独自React Hooks wrapper**を採用する。

### 構成

```typescript
@common-auth/react
├── AuthProvider     // Context Provider
├── useAuth          // Main Hook
├── AuthGuard        // Route Guard Component
└── utils/
    └── oidcClient   // oidc-client-ts wrapper
```

### 主要コンポーネント

#### 1. AuthProvider

```typescript
import { UserManager, User } from 'oidc-client-ts';

interface AuthProviderProps {
  authority: string;           // Keycloak issuer URL
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  children: React.ReactNode;
}

export function AuthProvider({ 
  authority, 
  clientId, 
  redirectUri, 
  postLogoutRedirectUri,
  children 
}: AuthProviderProps) {
  const userManager = new UserManager({
    authority,
    client_id: clientId,
    redirect_uri: redirectUri,
    post_logout_redirect_uri: postLogoutRedirectUri,
    response_type: 'code',
    scope: 'openid profile email',
    automaticSilentRenew: true
  });
  
  // ... state management ...
}
```

#### 2. useAuth Hook

```typescript
interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Phase 1
  login: () => Promise<void>;
  logout: () => Promise<void>;
  
  // Phase 2
  register: () => void;           // Keycloak登録ページへリダイレクト
  resetPassword: () => void;      // パスワードリセットページへリダイレクト
  configureMFA: () => void;       // MFA設定ページへリダイレクト
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

#### 3. AuthGuard Component

```typescript
interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onUnauthenticated?: () => void;  // カスタムハンドラー（ライブラリ非依存）
}

export function AuthGuard({ 
  children, 
  fallback,
  onUnauthenticated 
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, login } = useAuth();
  
  if (isLoading) {
    return <>{fallback || <div>Loading...</div>}</>;
  }
  
  if (!isAuthenticated) {
    // カスタムハンドラーがあればそれを実行
    if (onUnauthenticated) {
      onUnauthenticated();
      return null;  // リダイレクト中
    }
    
    // デフォルト: ログインページへ遷移
    login();
    return null;
  }
  
  return <>{children}</>;
}
```

**使用例（React Router v6）**:
```tsx
<Route path="/dashboard" element={
  <AuthGuard>
    <Dashboard />
  </AuthGuard>
} />
```

**使用例（Next.js App Router）**:
```tsx
'use client';

export default function ProtectedPage() {
  const router = useRouter();
  
  return (
    <AuthGuard 
      onUnauthenticated={() => router.push('/login')}
    >
      <Dashboard />
    </AuthGuard>
  );
}
```

**使用例（カスタムハンドラー）**:
```tsx
<AuthGuard 
  onUnauthenticated={() => {
    // ログイン前のパスを保存
    sessionStorage.setItem('returnUrl', window.location.pathname);
    login();
  }}
>
  <ProtectedContent />
</AuthGuard>
```

## 選択肢

### 選択肢A: oidc-client-ts + 独自wrapper（採用）

- **メリット**: 
  - OIDC標準準拠、IdP非依存（Keycloak以外への移行が容易）
  - 低レベルAPIへのアクセス可能（カスタマイズ性が高い）
  - 軽量（依存が少ない）
  - ADR-005で既に選定済み（一貫性）
  - 独自wrapperにより、プロジェクト固有のニーズに対応可能
- **デメリット**: 
  - React統合を自前実装する必要がある
  - 初期実装コスト（ただし、Phase 1の経験で軽減）

### 選択肢B: react-oidc-context

`oidc-client-ts`の公式React wrapper。

- **メリット**: 
  - 公式サポート（`oidc-client-ts`と同じメンテナ）
  - React統合が既に実装済み
  - コミュニティサポート
- **デメリット**: 
  - APIがやや低レベル（開発者にOIDCの深い理解を要求）
  - カスタマイズが難しい（例: MFA設定ページへのリダイレクト等）
  - プロジェクト固有のニーズに対応しづらい

### 選択肢C: Auth0 React SDK

- **メリット**: 
  - 成熟したSDK、優れた開発者体験
  - ドキュメントが充実
- **デメリット**: 
  - Auth0固有の実装（IdP依存）
  - Keycloakとの互換性が不完全
  - ライセンス制約（商用利用で費用発生の可能性）
  - ポータビリティの原則に反する

### 選択肢D: 完全独自実装（OIDC手動実装）

- **メリット**: 
  - 完全なコントロール
  - 軽量（不要な機能なし）
- **デメリット**: 
  - セキュリティリスク（OIDC実装の複雑さ、PKCE等）
  - 実装・テストコストが非常に高い
  - メンテナンス負荷
  - "Don't Roll Your Own Auth"原則に反する

## 結果

### 実装への影響

1. **新規パッケージ**: `packages/frontend-sdk/`
   ```
   frontend-sdk/
   ├── package.json          # @common-auth/react
   ├── tsconfig.json
   ├── tsup.config.ts        # ビルド設定（ESM + CJS）
   ├── src/
   │   ├── index.ts
   │   ├── AuthProvider.tsx
   │   ├── useAuth.ts
   │   ├── AuthGuard.tsx
   │   ├── types.ts
   │   └── utils/
   │       └── oidcClient.ts
   └── tests/
       ├── AuthProvider.test.tsx
       └── useAuth.test.ts
   ```

2. **依存関係**:
   ```json
   {
     "dependencies": {
       "oidc-client-ts": "^3.0.1",
       "react": "^18.0.0"
     },
     "devDependencies": {
       "@testing-library/react": "^14.0.0",
       "@testing-library/react-hooks": "^8.0.0",
       "typescript": "^5.0.0",
       "tsup": "^8.0.0"
     }
   }
   ```

3. **Example App** (`examples/react-app/`):
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
         <Routes>
           <Route path="/login" element={<Login />} />
           <Route path="/callback" element={<Callback />} />
           <Route path="/dashboard" element={
             <AuthGuard>
               <Dashboard />
             </AuthGuard>
           } />
         </Routes>
       </AuthProvider>
     );
   }
   
   function Dashboard() {
     const { user, logout, configureMFA } = useAuth();
     
     return (
       <div>
         <h1>Welcome, {user?.profile.email}</h1>
         <button onClick={logout}>Logout</button>
         <button onClick={configureMFA}>Setup MFA</button>
       </div>
     );
   }
   ```

### トレードオフ

#### メリット
- **IdP非依存**: Keycloak以外（Auth0, Azure AD B2C等）への移行が容易
- **カスタマイズ性**: プロジェクト固有の要件に柔軟に対応
- **軽量**: 必要最小限の機能のみ実装
- **学習コスト低**: Reactの標準パターン（Context + Hooks）を使用

#### デメリット
- **初期実装コスト**: React統合を自前実装（ただし、2-3日程度で完了見込み）
- **メンテナンス責任**: 公式SDKと異なり、バグ修正やアップデートは自前
  - **対策**: `oidc-client-ts`本体は公式サポート、wrapperは薄い層なので影響少
- **コミュニティサポート**: 公式SDKと比較してコミュニティが小さい
  - **対策**: ドキュメントを充実させる、社内での知見共有

### Phase 2での実装範囲

Phase 2bで以下を実装:
1. `AuthProvider`, `useAuth`, `AuthGuard`の基本実装
2. TypeScript型定義
3. 単体テスト（Jest + React Testing Library）
4. Example App（Login, Logout, Dashboard, MFA設定デモ）
5. README（導入手順、API Reference）

Phase 3以降で拡張検討:
- トークンリフレッシュのカスタマイズ
- エラーハンドリング強化
- ローディング状態の詳細化
- ユーザー情報キャッシュ戦略

### テスト戦略

#### 1. ユニットテスト（Jest + React Testing Library）

**useAuth Hookのテスト**:
```typescript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from './useAuth';
import { AuthProvider } from './AuthProvider';

describe('useAuth', () => {
  it('should login successfully', async () => {
    const wrapper = ({ children }) => (
      <AuthProvider
        authority="http://localhost:8080/realms/test"
        clientId="test-client"
        redirectUri="http://localhost:3000/callback"
        postLogoutRedirectUri="http://localhost:3000"
      >
        {children}
      </AuthProvider>
    );
    
    const { result } = renderHook(() => useAuth(), { wrapper });
    
    act(() => {
      result.current.login();
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });
});
```

#### 2. UserManager依存注入パターン

```typescript
// AuthProvider.tsx
interface AuthProviderProps {
  children: React.ReactNode;
  authority: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  userManager?: UserManager;  // テスト用に注入可能
}

export function AuthProvider({
  children,
  userManager: externalUserManager,
  ...config
}: AuthProviderProps) {
  const userManager = useMemo(() => {
    // 外部から注入されていればそれを使用（テスト用）
    if (externalUserManager) {
      return externalUserManager;
    }
    
    // 通常はここで生成
    return new UserManager({
      authority: config.authority,
      client_id: config.clientId,
      // ...
    });
  }, [externalUserManager, config]);
  
  // ...
}
```

**テストでの使用**:
```typescript
const mockUserManager = {
  signinRedirect: jest.fn(),
  signoutRedirect: jest.fn(),
  getUser: jest.fn().mockResolvedValue(mockUser),
  events: {
    addUserLoaded: jest.fn(),
    addUserUnloaded: jest.fn(),
    addAccessTokenExpired: jest.fn(),
  }
} as unknown as UserManager;

<AuthProvider
  authority="..."
  clientId="..."
  redirectUri="..."
  postLogoutRedirectUri="..."
  userManager={mockUserManager}
>
  {children}
</AuthProvider>
```

#### 3. MSW (Mock Service Worker)によるOIDCエンドポイントモック

```typescript
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  // OIDC Discovery
  http.get('http://localhost:8080/realms/test/.well-known/openid-configuration', () => {
    return HttpResponse.json({
      issuer: 'http://localhost:8080/realms/test',
      authorization_endpoint: 'http://localhost:8080/realms/test/protocol/openid-connect/auth',
      token_endpoint: 'http://localhost:8080/realms/test/protocol/openid-connect/token',
      userinfo_endpoint: 'http://localhost:8080/realms/test/protocol/openid-connect/userinfo',
      jwks_uri: 'http://localhost:8080/realms/test/protocol/openid-connect/certs',
    });
  }),
  
  // JWKS
  http.get('http://localhost:8080/realms/test/protocol/openid-connect/certs', () => {
    return HttpResponse.json({
      keys: [/* mock JWKS */]
    });
  }),
  
  // Token Exchange
  http.post('http://localhost:8080/realms/test/protocol/openid-connect/token', () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      id_token: 'mock-id-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'Bearer',
      expires_in: 300
    });
  }),
];
```

**setup.ts**:
```typescript
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

#### 4. E2Eテスト（Playwright）

```typescript
import { test, expect } from '@playwright/test';

test('user can login and access protected page', async ({ page }) => {
  // アプリにアクセス
  await page.goto('http://localhost:3000');
  
  // Loginボタンクリック
  await page.click('button:text("Login")');
  
  // Keycloakログインページへリダイレクト（実際のKeycloak使用）
  await expect(page).toHaveURL(/.*realms.*protocol\/openid-connect\/auth.*/);
  
  // ログイン実行
  await page.fill('input[name="username"]', 'testuser@example.com');
  await page.fill('input[name="password"]', 'password');
  await page.click('input[type="submit"]');
  
  // コールバック後、ダッシュボードへ
  await expect(page).toHaveURL('http://localhost:3000/dashboard');
  await expect(page.locator('h1')).toContainText('Welcome');
});
```

### Keycloak連携の実装パターン

Phase 2機能（登録、パスワードリセット、MFA設定）は、Keycloakの標準UIへのリダイレクトで実装:

```typescript
export function useAuth(): AuthContextValue {
  // ...
  
  const register = () => {
    const registerUrl = `${authority}/protocol/openid-connect/registrations?client_id=${clientId}&redirect_uri=${redirectUri}`;
    window.location.href = registerUrl;
  };
  
  const resetPassword = () => {
    const resetUrl = `${authority}/login-actions/reset-credentials?client_id=${clientId}`;
    window.location.href = resetUrl;
  };
  
  const configureMFA = () => {
    // 認証済みユーザーのみ
    if (!user) throw new Error('User must be authenticated');
    
    const mfaUrl = `${authority}/account/totp`;
    window.location.href = mfaUrl;
  };
  
  return { user, isAuthenticated, login, logout, register, resetPassword, configureMFA };
}
```

このアプローチにより:
- フロントエンド側でのフォーム実装が不要（Keycloakが提供）
- セキュリティリスク低減（認証情報をフロントエンドで扱わない）
- Keycloak UIのカスタマイズはテーマ機能で対応（Phase 3検討）

## 参考

- [oidc-client-ts Documentation](https://authts.github.io/oidc-client-ts/)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 for Browser-Based Apps (RFC draft)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps)
- [PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [React Context API](https://react.dev/learn/passing-data-deeply-with-context)
- [ADR-005: OIDC Client-TS選定](./005-oidc-client-ts-for-frontend.md)
