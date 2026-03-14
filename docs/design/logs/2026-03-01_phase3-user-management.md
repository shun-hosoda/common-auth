# 設計会議記録 — Phase 3: ユーザー管理・アクセス制御

**日時**: 2026-03-01  
**参加者**: PM, Architect, DB Specialist, Security Specialist, Senior Engineer  
**ドメインペルソナ**: 認証基盤 / IDaaS (OWASP Top 10, OAuth 2.0 / OIDC仕様, NIST SP 800-63)

---

## 要件サマリー（PRD FR-020〜FR-027）

| ID | 機能 | 優先度 |
|----|------|--------|
| FR-020 | ダッシュボード画面（認証済みのみ） | Must |
| FR-021 | ログイン画面（未認証のエントリーポイント） | Must |
| FR-022 | ログアウト → ログイン画面へリダイレクト | Must |
| FR-023 | クライアント管理（super_adminのみ） | Must |
| FR-024 | ユーザー管理画面（tenant_adminのみ表示） | Must |
| FR-025 | ユーザー登録・編集（tenant_admin操作） | Must |
| FR-026 | ロールベースUI制御（userはユーザー管理不可） | Must |
| FR-027 | Keycloak UIへの委譲（カスタムテーマ対応可） | Should |

---

## 設計決定

### ロール設計

| ロール | Keycloak対応 | 権限 |
|--------|-------------|------|
| `super_admin` | Realm-level `admin` | テナント（クライアント）登録・全テナントのユーザー管理・設定変更 |
| `tenant_admin` | `manage-users`（Client Role: `realm-management`） | 自テナント内のユーザー一覧・作成・編集・無効化 |
| `user` | デフォルト（認証済み） | ログイン・プロフィール・MFA・パスワードリセット |

> **super_admin の位置づけ**: テナント（クライアント）を登録・管理するサービス運営者。
> 通常のKeycloakログイン画面（Theme適用済み）からログインし、Dashboard経由でテナント管理機能にアクセスする。
> Keycloak管理コンソール（`/admin`）への直接アクセスは**運用時には使用しない**設計。

### 画面遷移設計

```
/ (root)
 ├── 未ログイン → /login（Keycloakログイン画面へリダイレクト、Theme適用済み）
 └── ログイン済み → /dashboard

/dashboard [user以上]
 ├── user: プロフィール・ログアウト・MFA設定
 ├── tenant_admin: + ユーザー管理ボタン（/admin/users）
 └── super_admin: + クライアント管理ボタン（/admin/clients）

/admin/users [tenant_admin以上]
 └── カスタムReact UI（Backend Admin API経由）
     ユーザー一覧・作成・編集・無効化・PW/MFAリセット

/admin/clients [super_adminのみ]
 └── テナント（クライアント）登録・管理画面（Phase 3で実装）
     テナント一覧・新規登録・設定変更
```

### API設計

```
既存:
  GET  /auth/health     → ヘルスチェック
  GET  /auth/me         → 現在ユーザー情報

追加:
  GET  /auth/roles      → ユーザーのロール一覧

Backend Admin API（新規）:
  GET    /admin/users              → テナント内ユーザー一覧
  POST   /admin/users              → ユーザー新規作成
  GET    /admin/users/{user_id}    → ユーザー詳細取得
  PUT    /admin/users/{user_id}    → ユーザー情報更新
  DELETE /admin/users/{user_id}    → ユーザー無効化（論理削除）
  POST   /admin/users/{user_id}/reset-password → パスワードリセット
  POST   /admin/users/{user_id}/reset-mfa      → MFAリセット
```

**Backend Admin APIセキュリティ**:
- 全エンドポイントで `tenant_admin` 以上のロールをJWTから検証
- `tenant_id` クレームでテナント境界を強制フィルタリング
- Keycloak Admin REST APIをプロキシ（フロントから直接叩かない）
- レートリミット適用（既存Rate Limiting基盤を活用）

**Backend追加実装方針**:
- `/auth/me`のレスポンスにJWTの`realm_access.roles`を含める（すでに含まれる場合は確認）
- フロントはJWTクレームから直接ロールを取得可能のため、`/auth/roles`は補助的に必要に応じて追加

### Frontend SDK拡張

```typescript
// useAuth hookの拡張
interface AuthContextValue {
  // 既存
  user: User | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  
  // 追加
  hasRole: (role: string) => boolean;
}

// AuthGuardの拡張
interface AuthGuardProps {
  children: ReactNode;
  requiredRoles?: string[];  // 追加: ロール要件
  fallback?: ReactNode;      // 追加: 権限不足時の表示
}
```

### ユーザー管理実装方針

> **⚠️ 方針変更 (2026-03-14)**: ADR-010をOption B（Keycloak委譲）からOption A（カスタムReact実装）に変更

**現在の方針**: Backend Admin API + カスタムReact UI

※ エンドポイント一覧は上記「API設計」節を参照。

#### Keycloak Admin REST API 認証方式

Backend Admin APIがKeycloak Admin REST APIを叩く際の認証方式:

```
認証フロー: OAuth 2.0 client_credentials grant
Client ID:  admin-api-client（Confidential Client）
Client認証: client_id + client_secret
スコープ:   Keycloak Admin REST API（realm-management）
```

**設計詳細**:
1. Keycloakに `admin-api-client` をConfidential Clientとして登録
2. Service Account Rolesで `realm-management` のロール（`manage-users` 等）を付与
3. Backend起動時に `client_credentials` フローでアクセストークンを取得
4. トークンをキャッシュし、有効期限前に自動更新（token refresh）
5. フロントからのリクエスト → Backend JWTミドルウェアでユーザー権限検証 → Keycloak Admin APIへプロキシ

```
[Frontend]  →  [Backend Admin API]  →  [Keycloak Admin REST API]
  JWT(user)     ① JWTからrole/tenant_id検証
                ② client_credentialsトークンで
                   Keycloak Admin APIを呼び出し
                ③ tenant_id境界フィルタ適用
```

**セキュリティ**:
- `client_secret` は環境変数（`KC_ADMIN_CLIENT_SECRET`）で管理、コードにハードコードしない
- Backend APIのミドルウェアでユーザーJWTの `tenant_admin` 以上ロールを検証した後にのみKeycloak APIを呼び出す
- `tenant_id` クレームでテナント境界を強制フィルタリング（super_adminのみ全テナントアクセス可）

#### フロントエンド（React）

- `/admin/users` にカスタムユーザー管理画面を実装
- Backend Admin API 経由で操作（フロントから直接Keycloak Admin APIは叩かない）
- PC/SP対応レスポンシブUI（既存admin-users.md画面仕様を踏襲）

### Keycloak Theme カスタマイズ方針

> **追加 (2026-03-14)**

#### 設計原則

1. **CSSのみでカスタマイズ**: `.ftl`（Freemarkerテンプレート）の構造変更は最小限に留める
2. **CSS変数ベース**: 共通テーマで `--primary-color` 等のCSS変数を定義し、顧客ごとにCSSファイルだけ差し替え
3. **Keycloakバージョン互換性**: テンプレートHTML構造に依存しないため、Keycloakアップデート時の破損リスクを最小化

#### テーマ構成

```
auth-stack/keycloak/themes/
└── common-auth/
    └── login/
        ├── theme.properties        # テーマメタ情報
        ├── resources/
        │   └── css/
        │       └── styles.css      # 共通CSS（CSS変数定義）
        └── (将来: 顧客別CSSオーバーライド)
```

#### CSS変数定義（共通テーマ）

```css
:root {
  --primary-color: #2563eb;       /* メインカラー */
  --primary-hover: #1d4ed8;       /* ホバー時 */
  --bg-color: #f8fafc;            /* 背景色 */
  --card-bg: #ffffff;             /* カード背景 */
  --text-color: #1e293b;          /* テキスト色 */
  --border-radius: 8px;           /* 角丸 */
  --logo-url: none;               /* ロゴ画像（顧客別に変更） */
}
```

#### 顧客別カスタマイズの方法

- CSS変数の値を上書きするだけで、ロゴ・メインカラー・背景色を変更可能
- `.ftl`ファイルの編集は禁止（Keycloakアップデート時にログイン不能リスク）
- Realm設定で `loginTheme: "common-auth"` を指定

### Keycloak設定変更（realm-export.json）

1. Realm Roleとして`super_admin`、`tenant_admin`を追加
2. テストユーザー（`admin@example.com`）に`tenant_admin`を付与
3. `super_admin`ユーザー（`superadmin@example.com`）を追加
4. Client Roleマッピング：`tenant_admin` → `manage-users`（realm-management）

### DB設計変更

追加不要。ロール情報はKeycloakが管理する。  
アプリ側DBには業務データのみ（RLSで既にtenant_id分離済み）。

---

## 議論のポイント

1. **ユーザー管理UI: カスタム実装に変更**
   - PM・Arch: MVP時は工数削減でKeycloak委譲（Option B）を選択したが、テナント境界やUXの要件を考慮しOption A（カスタムReact + Backend Admin API）に変更
   - Sec: Backend Admin APIでテナント境界を強制することで、Keycloak管理コンソールの認可範囲漏れリスクを解消
   - ADR-010をSupersededとして更新済み

2. **フロントのロールチェック**
   - Sec: JWTクレーム（`realm_access.roles`）から取得するが、UI制御のみ。API側でも必ずバックエンド検証を行う
   - Eng: `hasRole()`をuseAuthに追加してフロント実装を簡略化

3. **Keycloak Themes**
   - Arch: CSS変数ベースでテンプレート構造に依存しない方針
   - Sec: `.ftl`ファイル編集禁止（Keycloakアップデート時のログイン不能リスク回避）
   - 顧客別カスタマイズはCSS変数の上書きのみで実現

4. **super_adminのスコープ**
   - Arch: テナント（クライアント）を登録・管理するサービス運営者。通常のKeycloakログイン画面からログインし、Dashboard経由で管理機能へアクセス
   - Sec: Keycloak管理コンソール直接アクセスは運用では使わない設計。Admin APIプロキシ経由で必要な操作のみ許可
   - PM: MVPではテストユーザーとして準備、Phase 3でテナント管理画面（`/admin/clients`）も実装

---

## 起票すべきADR

- **ADR-010**: ユーザー管理UI実装方針（Keycloak委譲 vs カスタム実装）
- **ADR-011**: ロールベースアクセス制御設計（Keycloakロール + JWTクレーム）

---

## 次のアクション

- [ ] `realm-export.json` にロール追加（super_admin, tenant_admin, テストユーザー）
- [ ] Frontend SDK: `hasRole()` を `useAuth` に追加
- [ ] Frontend SDK: `AuthGuard` に `requiredRoles` を追加
- [ ] Backend Admin API: Keycloak Admin REST APIプロキシ実装（/admin/users）
- [ ] React example app: Dashboard にロールベース表示制御を追加
- [ ] React example app: `/admin/users` カスタムユーザー管理画面を実装
- [ ] React example app: `/admin/clients` テナント管理画面を実装（super_admin用）
- [ ] Keycloak: `admin-api-client`（Confidential Client）を作成、Service Account Roles設定
- [ ] Keycloak Theme: `auth-stack/keycloak/themes/common-auth/` を作成
- [ ] ADR-011（RBAC設計）を起票
- [ ] 設計レビュー（/review --design）
