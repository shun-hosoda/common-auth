# Frontend Example App 設計書

## 1. 概要

### 目的
`@common-auth/react` SDKの実装例として、Keycloak統合を含む完全な認証フローを示すReactアプリケーションを提供する。

### 対象ユーザー
- `@common-auth/react` SDKを利用する開発者
- Keycloak統合の実装パターンを参照したい開発者

### スコープ
- ログイン・ログアウト
- 2要素認証（TOTP）
- パスワードリセット（メール通知経由）
- ユーザー登録
- 保護されたルート（Dashboard）

## 2. 技術スタック

| 項目 | 選定技術 | 理由 |
|------|----------|------|
| ビルドツール | Vite | 高速な開発体験、TypeScript/Reactのゼロコンフィグサポート |
| フレームワーク | React 18 | SDKのターゲットフレームワーク |
| 言語 | TypeScript | 型安全性、SDK APIとの整合性 |
| ルーティング | React Router v6 | 標準的なReactルーティングライブラリ |
| 認証SDK | @common-auth/react | 本プロジェクトのフロントエンドSDK |
| スタイリング | CSS（素のCSS） | 依存を最小化、カスタマイズ容易性 |

## 3. 画面構成

### 3.1. Home（ログイン前）
- **パス**: `/`
- **目的**: 未認証ユーザー向けエントリーポイント
- **コンポーネント**: `src/pages/Home.tsx`
- **主要機能**:
  - Login ボタン → Keycloakログイン画面へリダイレクト
  - Register ボタン → Keycloakユーザー登録画面へリダイレクト
  - Forgot password? リンク → Keycloakパスワードリセット画面へリダイレクト
  - 機能説明カード表示（OIDC+PKCE、2FA、パスワードリセット、自己登録）

### 3.2. Callback
- **パス**: `/callback`
- **目的**: OIDC認証後のリダイレクトURIとして機能
- **コンポーネント**: `src/pages/Callback.tsx`
- **主要機能**:
  - `useAuth().handleCallback()`でトークン処理（AuthProvider管理下のUserManagerを使用）
  - 認証成功 → `/dashboard`へ自動遷移
  - 認証失敗 → エラーメッセージ表示、Homeへ戻るボタン
- **エラーハンドリング**:
  - Keycloak接続エラー時: エラーメッセージ表示＋Homeへ戻るボタン
  - 状態コード不正時: エラーメッセージ表示＋Homeへ戻るボタン

### 3.3. Dashboard（認証後）
- **パス**: `/dashboard`
- **目的**: 認証済みユーザー向けメイン画面
- **コンポーネント**: `src/pages/Dashboard.tsx`
- **保護**: `AuthGuard`で保護、未認証の場合は自動的にログインへ
- **主要機能**:
  - ユーザープロフィール表示（名前、メール、アバター）
  - アクションボタン:
    - Setup MFA → Keycloakアカウントコンソールへリダイレクト
    - Copy Access Token → アクセストークンをクリップボードへコピー（**開発環境のみ**: `import.meta.env.DEV`で制御）
    - Logout → ログアウト実行
  - ユーザープロフィールJSON表示（デバッグ用）
  - トークン情報表示（有効期限、スコープ）
- **セキュリティ考慮**:
  - トークンコピー機能は本番ビルドでは非表示

## 4. 画面遷移フロー

```
┌─────────────────────────────────────────────────────────────────┐
│ Home (/)                                                        │
│  [Login] [Register] [Forgot password?]                        │
└────┬──────────────┬────────────────┬──────────────────────────┘
     │              │                │
     ▼              ▼                ▼
┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐
│ Keycloak    │ │ Keycloak     │ │ Keycloak            │
│ Login       │ │ Registration │ │ Password Reset      │
└─────┬───────┘ └──────┬───────┘ └─────┬───────────────┘
      │                │                │
      ▼                │                ▼
┌─────────────┐        │          ┌─────────────────────┐
│ Keycloak    │        │          │ Email Notification  │
│ MFA (TOTP)  │        │          └─────┬───────────────┘
└─────┬───────┘        │                │
      │                │                ▼
      ▼                │          ┌─────────────────────┐
┌─────────────────────┐│          │ Keycloak            │
│ Callback (/callback)││          │ New Password        │
└─────┬───────────────┘│          └─────────────────────┘
      │                │
      ▼                │
┌─────────────────────────────────────────────────┐
│ Dashboard (/dashboard) [AuthGuard Protected]    │
│  User Profile | [Setup MFA] [Logout]           │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼ Setup MFA
            ┌─────────────────────┐
            │ Keycloak            │
            │ Account Console     │
            │ (TOTP Setup)        │
            └─────────────────────┘
```

## 5. 認証フローの詳細

### 5.1. ログインフロー

```
1. ユーザーが Home で [Login] をクリック
   ↓
2. useAuth().login() が呼ばれる
   ↓
3. AuthProvider内で userManager.signinRedirect() 実行
   ↓
4. ブラウザがKeycloakログイン画面へリダイレクト
   ↓
5. ユーザーが認証情報を入力
   ↓
6. [2FAが有効な場合] TOTPコード入力画面表示
   ↓
7. 認証成功 → /callback?code=xxx&state=xxx へリダイレクト
   ↓
8. Callback コンポーネントで signinRedirectCallback() 実行
   ↓
9. トークン取得・保存 → /dashboard へ遷移
   ↓
10. AuthGuard が認証状態を確認 → Dashboard表示
```

### 5.2. パスワードリセットフロー

```
1. ユーザーが Home で [Forgot password?] をクリック
   ↓
2. useAuth().resetPassword() が呼ばれる
   ↓
3. Keycloakパスワードリセット画面へリダイレクト
   ↓
4. ユーザーがメールアドレスを入力
   ↓
5. Keycloakがリセットメールを送信（SMTP設定が必要）
   ↓
6. ユーザーがメール内のリンクをクリック
   ↓
7. Keycloak新パスワード設定画面へ遷移
   ↓
8. 新パスワード入力・確認
   ↓
9. パスワード更新完了 → Keycloakログイン画面へ
   ↓
10. ユーザーが新パスワードでログイン → /callback → /dashboard
```

### 5.3. MFA設定フロー

```
1. ユーザーが Dashboard で [Setup MFA] をクリック
   ↓
2. useAuth().configureMFA() が呼ばれる
   ↓
3. Keycloakアカウントコンソール（/account）へリダイレクト
   ↓
4. ユーザーが「Signing In」→「Authenticator Application」を選択
   ↓
5. QRコードを表示 → スマホの認証アプリでスキャン
   ↓
6. 認証アプリに生成されたコードを入力
   ↓
7. MFA設定完了 → 次回ログインから2FAが要求される
```

## 6. コンポーネント設計

### 6.1. AuthProvider（SDK提供）
- **責務**: OIDC認証のライフサイクル管理
- **機能**:
  - `UserManager`の初期化
  - ユーザーロード・イベント監視
  - Silent Renew（自動トークン更新）
  - 認証アクション提供（login, logout, register, resetPassword, configureMFA）

### 6.2. useAuth（SDK提供）
- **責務**: コンポーネントから認証状態・アクションへのアクセス提供
- **返却値**:
  - `user`: OIDCユーザーオブジェクト
  - `isAuthenticated`: 認証状態
  - `isLoading`: 初期ロード中フラグ
  - `login()`, `logout()`, `register()`, `resetPassword()`, `configureMFA()`, `getAccessToken()`

### 6.3. AuthGuard（SDK提供）
- **責務**: ルート保護、未認証時の動作制御
- **Props**:
  - `fallback`: ロード中に表示するUI
  - `onUnauthenticated`: 未認証時のコールバック（デフォルト: `login()`）
- **動作**:
  - `isLoading === true` → fallback表示
  - `isAuthenticated === false` → `onUnauthenticated()`実行
  - `isAuthenticated === true` → children表示

### 6.4. Home.tsx
- **責務**: ランディングページとログインエントリーポイント
- **状態管理**:
  - 既に認証済みの場合 → `/dashboard`へ自動リダイレクト
- **UI要素**:
  - ナビゲーションバー
  - ヒーローセクション（タイトル、説明、アクションボタン）
  - 機能カード（4つの主要機能を説明）

### 6.5. Callback.tsx
- **責務**: OIDC認証コールバックの処理
- **エラーハンドリング**:
  - 認証失敗時はエラーメッセージを表示
  - Homeへ戻るボタンを提供
- **成功時**: `/dashboard`へ自動遷移

### 6.6. Dashboard.tsx
- **責務**: 認証後のメイン画面
- **表示情報**:
  - ユーザーアバター（イニシャル）
  - ユーザー名・メールアドレス
  - アクションボタン群
  - プロフィール詳細（JSON）
  - トークン情報（有効期限、スコープ）

## 7. 設定

### 7.1. OIDC設定（main.tsx）
```typescript
const AUTH_CONFIG = {
  authority: 'http://localhost:8080/realms/common-auth',
  clientId: 'frontend-app',
  redirectUri: 'http://localhost:3000/callback',
  postLogoutRedirectUri: 'http://localhost:3000',
}
```

### 7.2. Keycloakクライアント設定要件
- **Client ID**: `frontend-app`
- **Client authentication**: OFF（Public Client）
- **Valid redirect URIs**: `http://localhost:3000/*`
- **Valid post logout redirect URIs**: `http://localhost:3000/*`
- **Web origins**: `http://localhost:3000`

### 7.3. SMTP設定（パスワードリセットに必要）
`auth-stack/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@example.com
```

## 8. セキュリティ考慮事項

### 8.1. OIDC Authorization Code + PKCE
- Public Clientでもセキュアな認証フローを実現
- `oidc-client-ts`が自動的にPKCEを適用

### 8.2. トークン管理
- アクセストークン、リフレッシュトークンは`oidc-client-ts`が管理
- セッションストレージへ保存（XSS対策でlocalStorageは不使用）
- トークンコピー機能は開発環境のみで有効化（`import.meta.env.DEV`）し、本番環境でのトークン漏洩リスクを回避

### 8.3. UserManager一元管理
- `AuthProvider`が唯一の`UserManager`インスタンスを保持
- 各コンポーネントは`useAuth()`経由でアクションを呼び出し、直接`UserManager`を生成しない
- トークンストレージの二重管理を防止

### 8.4. CORS
- Keycloakの`Web origins`設定により、フロントエンドからのリクエストを許可

### 8.5. リダイレクトURI検証
- Keycloakが`Valid redirect URIs`を厳格に検証
- ワイルドカード（`/*`）の範囲を必要最小限に限定

## 9. 非機能要件

### 9.1. パフォーマンス
- Viteによる高速な開発ビルド（< 1秒）
- 本番ビルド後のバンドルサイズ: 
  - `dist/index.js`: ~6.5KB (CJS)
  - `dist/index.mjs`: ~5.0KB (ESM)
  - （gzip圧縮前、Frontend SDK本体のみ）
- Example App全体のバンドルサイズは未測定（TODO）

### 9.2. エラーハンドリング
- `AuthProvider`は`error`状態を管理
- Keycloak接続エラー時: Callbackページでエラーメッセージ表示
- Silent Renew失敗時: `error`状態に保存、必要に応じてログイン画面へ誘導
- トークン期限切れ時: `user.expired`フラグを確認、`isAuthenticated`がfalseになる

### 9.3. ユーザビリティ
- ローディング状態の明示（`isLoading`フラグ）
- エラーメッセージの表示
- レスポンシブデザイン対応

### 9.4. 保守性
- TypeScriptによる型安全性
- コンポーネントの責務分離
- SDK APIへの依存を最小化（変更容易性）

## 10. 今後の拡張可能性

### 10.1. ロール・権限管理
- Keycloakのロールクレームをトークンから取得
- ロールベースのルート保護（`<AuthGuard requiredRoles={['admin']}>`）

### 10.2. マルチテナント対応
- テナントIDをOIDC追加パラメータとして渡す
- テナント固有のブランディング切り替え

### 10.3. E2Eテスト
- Playwright/Cypressによる認証フローのE2Eテスト追加

### 10.4. SSR/SSG対応
- Next.js版の実装例追加
- サーバーサイドでのトークン検証

## 11. 参考情報

- [OIDC Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [oidc-client-ts](https://github.com/authts/oidc-client-ts)
