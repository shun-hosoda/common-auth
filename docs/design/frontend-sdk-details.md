# Frontend SDK 設計書

Frontend SDK（`@common-auth/react`）の実装仕様。AuthProvider、useAuth Hook、AuthGuardを含む。

---

## 1. パッケージ構成

```
packages/frontend-sdk/
├── package.json              # @common-auth/react
├── tsconfig.json
├── tsup.config.ts
├── src/
│   ├── index.ts              # エクスポート
│   ├── AuthProvider.tsx       # Context Provider
│   ├── AuthContext.ts        # React Context定義
│   ├── useAuth.ts            # Main Hook
│   ├── AuthGuard.tsx         # Route Guard Component
│   └── types.ts              # TypeScript型定義
```

---

## 2. useAuth Hook

```typescript
interface AuthContextValue {
  // 認証状態
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  
  // 認証操作
  login: () => Promise<void>;
  logout: () => Promise<void>;
  
  // Keycloakページへのリダイレクト
  register: () => void;           // 登録ページ
  resetPassword: () => void;      // パスワードリセットページ
  configureMFA: () => void;       // MFA設定（kc_action: CONFIGURE_TOTP）
  handleCallback: () => Promise<void>;  // OIDCコールバック処理
  
  // トークン・ロール
  getAccessToken: () => string | null;  // アクセストークン取得
  hasRole: (role: string) => boolean;   // ロール判定
}
```

> `extractRealmRoles()` はアクセストークン優先で読む（Keycloak が ID token にロールを含めない設定の場合の防衛）。

---

## 3. AuthProvider

```typescript
interface AuthProviderProps {
  children: React.ReactNode;
  authority: string;              // Keycloak issuer URL
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri?: string; // 省略時はredirectUriを使用
  scope?: string;                 // デフォルト: 'openid profile email'
  automaticSilentRenew?: boolean; // デフォルト: true
}
```

- `oidc-client-ts` の `UserManager` をラップ
- `automaticSilentRenew: true` でアクセストークン自動更新
- `response_type: 'code'` / `scope: 'openid profile email'`
- UserManager は AuthProvider 内で一元管理（複数インスタンス生成禁止）

---

## 4. AuthGuard

```typescript
interface AuthGuardProps {
  children: ReactNode;
  requiredRoles?: string[];         // ロール要件
  fallback?: ReactNode;             // ローディング中の表示
  onUnauthenticated?: () => void;   // 未認証時のコールバック（デフォルト: login()）
  unauthorizedFallback?: ReactNode; // 権限不足時の表示（デフォルト: "Access Denied"）
}
```

- `isAuthenticated` でルートを保護
- `requiredRoles` 指定時は `hasRole()` も検証（OR条件: いずれか1つのロールを持っていればOK）
- `onUnauthenticated` 未指定時は自動で `login()` を実行
- フロントのRBACはUI制御のみ。API側でも必ずバックエンド検証を行う

---

## 5. 技術スタック

| 項目 | 選定技術 | 根拠 |
|------|---------|------|
| OIDC | oidc-client-ts | [ADR-005](../adr/005-oidc-client-ts-for-frontend.md) / [ADR-008](../adr/008-frontend-sdk-technology.md) |
| React | 18+ | SDKのターゲットフレームワーク |
| TypeScript | 5+ | 型安全性 |
| ビルド | tsup | ESM + CJS デュアル出力 |

---

## 6. セキュリティ考慮

- アクセストークンはメモリ保持（`sessionStorage` 経由、XSS対策）
- リフレッシュトークンは `automaticSilentRenew` で自動管理
- CORS: Keycloak + Frontend origin のみ許可
- CSP: strict デフォルト + config でカスタマイズ可能

---

## 7. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-005](../adr/005-oidc-client-ts-for-frontend.md) | oidc-client-ts |
| [ADR-008](../adr/008-frontend-sdk-technology.md) | AuthProvider + useAuth + AuthGuard |

---

*元ログ: [設計会議記録 — Phase 2 機能拡張](logs/2026-03-01_190131_phase2-features.md)*
