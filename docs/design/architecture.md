# システムアーキテクチャ設計書

## 1. 概要

複数プロジェクトで再利用可能なポータブル認証プラットフォーム。
Keycloak（Docker）をIdPとして採用し、認証ロジックの自前実装を回避する。

### 設計原則

- ステートレス & スケーラブルなJWTベースアーキテクチャ
- Frontend SDK（React Hooks）+ Backend SDK（FastAPI Middleware）として配布
- マルチテナント対応（Shared Realm + Groups）
- クラウド非依存（Docker Composeベース）

## 2. アーキテクチャ

### レイヤー構成

**Auth Stack**（Keycloak + PostgreSQL）と **SDK Layer**（Frontend/Backend）を完全分離。

```
┌──────────────────────────────┐
│       Frontend App           │
│    (@common-auth/react)      │
│  ・AuthProvider / useAuth    │
│  ・AuthGuard                 │
└─────────┬────────────────────┘
          │ OIDC AuthCode + PKCE
          ▼
┌──────────────────────────────┐
│       Keycloak (IdP)         │
│  ・ユーザー認証              │
│  ・MFA / パスワードリセット  │
│  ・トークン発行 (RS256)      │
└──────────────────────────────┘
          │ JWT
          ▼
┌──────────────────────────────┐
│       Backend App            │
│    (common-auth Python)      │
│  ・JWT検証ミドルウェア       │
│  ・Admin API (KC Proxy)      │
│  ・Rate Limiting             │
└──────────────────────────────┘
```

- Auth Stack: Docker Composeで顧客環境に独立デプロイ
- SDK Layer: npm / PyPI パッケージとして配布
- バックエンド: ステートレス（セッション不使用、JWT検証のみ）

## 3. 認証フロー

- **OIDC Authorization Code Flow + PKCE**（OAuth 2.1推奨）
- RS256署名、JWKS公開鍵キャッシュ（TTL 24h、未知kid即時refresh）
- Implicit Flow / Password Grant は禁止

## 4. API設計（Backend SDK提供）

### 認証ルーター（/auth）

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/auth/me` | 現在のユーザー情報取得 | 必要 |
| GET | `/auth/health` | Auth Stack死活監視 | 不要 |
| POST | `/auth/logout` | ログアウト（ログ記録のみ。実際のトークン失効はフロントエンドOIDC signoutRedirectで処理） | 必要 |
| GET | `/auth/mfa-status` | MFA設定状態の取得 | 必要 |

### Admin API（/api/admin） — Backend SDKに内蔵

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/api/admin/users` | テナント内ユーザー一覧 | tenant_admin以上 |
| POST | `/api/admin/users` | ユーザー新規作成 | tenant_admin以上 |
| GET | `/api/admin/users/{user_id}` | ユーザー詳細取得 | tenant_admin以上 |
| PUT | `/api/admin/users/{user_id}` | ユーザー情報更新 | tenant_admin以上 |
| DELETE | `/api/admin/users/{user_id}` | ユーザー無効化（論理削除） | tenant_admin以上 |
| POST | `/api/admin/users/{user_id}/reset-password` | パスワードリセット | tenant_admin以上 |
| POST | `/api/admin/users/{user_id}/reset-mfa` | MFAリセット | tenant_admin以上 |
| GET | `/api/admin/clients` | テナント一覧 | super_admin |
| POST | `/api/admin/clients` | テナント作成 | super_admin |

> Admin APIは `setup_auth()` で自動マウントされる。Keycloak Admin REST APIを`admin-api-client`（client_credentials grant）経由でプロキシする。

## 5. DB設計方針

- **認証データ**: Keycloak内部DB（パスワード、MFA等）→ 業務DBに保持しない
- **業務DB**: `tenants` + `user_profiles` + グループ・権限管理テーブル群
- `user_profiles.id` = Keycloakの `sub` クレーム（不変UUID）
- Lazy Sync（JWT検証時にupsert）はオプトイン（`ENABLE_USER_SYNC=true`で有効化）
- RLSポリシーテンプレートを提供（`NULLIF` + `current_setting('app.current_tenant_id', true)` による安全な実装）
- グループ・権限管理: `tenant_groups`, `user_group_memberships`, `permissions`, `group_permissions`, `user_permissions`

## 6. マルチテナント設計

- Shared Realm + Groups + User Attribute（[ADR-003](../adr/003-multi-tenant-realm-isolation.md) 改訂済み）
- tenant_id取得のデフォルト: JWT `iss` クレームからRealm名を抽出
- 設定で切替可能: カスタムクレーム / 環境変数固定値

詳細は [マルチテナント設計書](multi-tenant.md) を参照。

## 7. セキュリティ設計

- SecurityHeadersミドルウェア（HSTS, CSP, X-Frame-Options等）
- Rate Limitingミドルウェア（[Backend SDK設計書](backend-sdk-details.md) 参照）
- CORS: Keycloak + Frontend origin のみ許可
- アクセストークンはメモリ保持（XSS対策）

## 8. 実装スタック

| 領域 | 技術選定 | 根拠 |
|------|---------|------|
| Backend SDK | Python / FastAPI / PyJWT + cryptography / httpx | [ADR-004](../adr/004-pyjwt-for-backend-jwt-verification.md) |
| Frontend SDK | React 18+ / TypeScript / oidc-client-ts | [ADR-005](../adr/005-oidc-client-ts-for-frontend.md) / [ADR-008](../adr/008-frontend-sdk-technology.md) |
| IdP | Keycloak (Docker) | [ADR-001](../adr/001-keycloak-as-idp.md) |
| 認証フロー | OIDC AuthCode + PKCE | [ADR-002](../adr/002-oidc-authorization-code-flow-pkce.md) |

導入コマンド:
```bash
pip install common-auth          # Backend SDK
npm install @common-auth/react   # Frontend SDK
```

環境変数3つ（`KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`）で動作。

## 9. プロジェクト構成

```
common-auth/
├── auth-stack/                 # Keycloakデプロイ構成
│   ├── docker-compose.yml      # 4サービス: keycloak, keycloak-db, app-db, mailhog
│   ├── .env.example
│   ├── keycloak/
│   │   └── realm-export.json
│   └── postgres/
│       └── init.sql            # 業務DB初期化（テーブル・RLS・テストデータ）
├── packages/
│   ├── frontend-sdk/           # @common-auth/react
│   └── backend-sdk/            # common-auth (Python)
├── examples/
│   ├── react-app/              # Frontend Example App
│   └── fastapi-app/            # Backend Example App
├── docs/
└── tests/
```

### Docker Compose構成（auth-stack）

| サービス | イメージ | ポート | 用途 |
|---------|---------|--------|------|
| keycloak | quay.io/keycloak/keycloak:24.0 | 8080 | IdP |
| keycloak-db | postgres:16-alpine | (内部) | Keycloak用DB |
| app-db | postgres:16-alpine | 5433 | 業務用DB（RLS・テストデータ） |
| mailhog | mailhog/mailhog:v1.0.1 | 1025/8025 | 開発用SMTPモック |

## 10. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-001](../adr/001-keycloak-as-idp.md) | IdPとしてKeycloakを採用 |
| [ADR-002](../adr/002-oidc-authorization-code-flow-pkce.md) | OIDC Authorization Code Flow + PKCE |
| [ADR-003](../adr/003-multi-tenant-realm-isolation.md) | Shared Realm + Groups（改訂済み） |
| [ADR-004](../adr/004-pyjwt-for-backend-jwt-verification.md) | PyJWT + cryptography |
| [ADR-005](../adr/005-oidc-client-ts-for-frontend.md) | oidc-client-ts |
| [ADR-006](../adr/006-defense-in-depth-rls.md) | 多層防御RLS |

---

*元ログ: [設計会議記録 — 共通認証・ユーザー管理モジュール](logs/2026-03-01_163700_auth-module.md)*
