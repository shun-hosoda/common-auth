# Phase 3 ユーザー管理・アクセス制御 設計書

## 1. 概要

管理者によるユーザー管理と、ロールベースのアクセス制御をカスタムReact UIで実装する。
Keycloak Admin REST APIをBackend Admin APIでプロキシし、テナント境界を強制する。

### 対象PRD要件

| ID | 機能 | 優先度 |
|----|------|--------|
| FR-020 | ダッシュボード画面 | Must |
| FR-021 | ログイン画面 | Must |
| FR-022 | ログアウト→リダイレクト | Must |
| FR-023 | クライアント管理（super_admin） | Must |
| FR-024 | ユーザー管理画面（tenant_admin） | Must |
| FR-025 | ユーザー登録・編集 | Must |
| FR-026 | ロールベースUI制御 | Must |
| FR-027 | Keycloak UIへの委譲 | Should |

---

## 2. ロール設計

| ロール | Keycloak対応 | 権限 |
|--------|-------------|------|
| `super_admin` | Realm-level `admin` | テナント登録・全テナントのユーザー管理・設定変更 |
| `tenant_admin` | `manage-users`（realm-management） | 自テナント内のユーザー一覧・作成・編集・無効化 |
| `user` | デフォルト（認証済み） | ログイン・プロフィール・MFA・パスワードリセット |

> **super_admin の位置づけ**: テナントを登録・管理するサービス運営者。
> 通常のKeycloakログイン画面からログインし、Dashboard経由で管理機能へアクセス。
> Keycloak管理コンソール（`/admin`）への直接アクセスは運用では使用しない。

### ロール関連 ADR

- [ADR-011](../adr/011-role-based-access-control.md): ロールベースアクセス制御設計

---

## 3. 画面遷移設計

```
/ (root)
 ├── 未ログイン → /login（Keycloakログイン画面へリダイレクト）
 └── ログイン済み → /dashboard

/dashboard [user以上]
 ├── user: プロフィール・ログアウト・MFA設定
 ├── tenant_admin: + ユーザー管理 + セキュリティ設定
 └── super_admin: + クライアント管理

/admin/users [tenant_admin以上]
 └── カスタムReact UI（Backend Admin API経由）

/admin/clients [super_adminのみ]
 └── テナント登録・管理画面

/security [tenant_admin以上]
 └── テナントMFAポリシー管理（Phase 3.5で追加）
```

---

## 4. Backend Admin API設計

### エンドポイント一覧

```
既存（/auth）:
  GET  /auth/health          → ヘルスチェック
  GET  /auth/me              → 現在ユーザー情報

Admin API（/api/admin）:
  GET    /api/admin/users              → テナント内ユーザー一覧
  POST   /api/admin/users              → ユーザー新規作成
  GET    /api/admin/users/{user_id}    → ユーザー詳細取得
  PUT    /api/admin/users/{user_id}    → ユーザー情報更新
  DELETE /api/admin/users/{user_id}    → ユーザー無効化（論理削除）
  POST   /api/admin/users/{user_id}/reset-password → PW リセット
  POST   /api/admin/users/{user_id}/reset-mfa      → MFA リセット
  GET    /api/admin/clients            → テナント一覧 (super_admin)
  POST   /api/admin/clients            → テナント作成 (super_admin)
```

### セキュリティ

- 全エンドポイントで `tenant_admin` 以上のロールをJWTから検証
- `tenant_id` クレームでテナント境界を強制フィルタリング
- Keycloak Admin REST APIをプロキシ（フロントから直接叩かない）
- Rate Limiting適用

### Keycloak Admin API認証方式

```
認証フロー: OAuth 2.0 client_credentials grant
Client ID:  admin-api-client (Confidential Client)
Client認証: client_id + client_secret
スコープ:   realm-management (manage-users 等)
```

```
[Frontend]  →  [Backend Admin API]  →  [Keycloak Admin REST API]
  JWT(user)     ① JWTからrole/tenant_id検証
                ② client_credentialsトークンで
                   Keycloak Admin APIを呼び出し
                ③ tenant_id境界フィルタ適用
```

- `client_secret` は環境変数（`KC_ADMIN_CLIENT_SECRET`）で管理
- トークンキャッシュ + 有効期限前自動更新

---

## 5. Frontend SDK拡張

### useAuth Hook追加

```typescript
interface AuthContextValue {
  // 既存
  user: User | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  
  // Phase 3追加
  hasRole: (role: string) => boolean;
}
```

### AuthGuard拡張

```typescript
interface AuthGuardProps {
  children: ReactNode;
  requiredRoles?: string[];   // ロール要件
  fallback?: ReactNode;       // 権限不足時の表示
}
```

> フロントのRBACはUI制御のみ。API側でも必ずバックエンド検証を行う。

---

## 6. Keycloak Theme カスタマイズ

### 設計原則

1. **CSSのみ**: `.ftl` テンプレートの構造変更は最小限
2. **CSS変数ベース**: 顧客ごとにCSSファイルのみ差し替え
3. **Keycloakバージョン互換性**: テンプレート構造に依存しない

### テーマ構成

```
auth-stack/keycloak/themes/
└── common-auth/
    └── login/
        ├── theme.properties
        └── resources/css/styles.css
```

### CSS変数定義

```css
:root {
  --primary-color: #2563eb;
  --primary-hover: #1d4ed8;
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-color: #1e293b;
  --border-radius: 8px;
  --logo-url: none;
}
```

顧客別カスタマイズ: CSS変数の値を上書きするだけでロゴ・カラー・背景を変更可能。
`.ftl` ファイル編集は禁止（Keycloakアップデート時のログイン不能リスク回避）。

---

## 7. Keycloak設定変更

- Realm Role追加: `super_admin`, `tenant_admin`
- テストユーザー: `admin@example.com`（tenant_admin）, `superadmin@example.com`（super_admin）
- `admin-api-client`（Confidential Client）: Service Account Roles で `realm-management` 付与
- Client Theme: `loginTheme: "common-auth"`

## 8. DB設計

追加不要。ロール情報はKeycloakが管理する。
アプリ側DBには業務データのみ（RLSで `tenant_id` 分離済み）。

---

## 9. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-010](../adr/010-user-management-ui-delegation.md) | カスタムReact実装（Keycloak委譲から変更） |
| [ADR-011](../adr/011-role-based-access-control.md) | ロールベースアクセス制御 |

---

*元ログ: [設計会議記録 — Phase 3: ユーザー管理・アクセス制御](logs/2026-03-01_phase3-user-management.md)*
