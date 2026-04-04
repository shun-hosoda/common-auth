# 設計サマリー

このファイルは全設計書の要約。詳細が必要な場合のみ個別ファイルを参照する。

## プロジェクト概要

**common-auth**: ポータブル認証基盤SDK
- **IdP**: Keycloak (Docker)
- **Backend**: Python/FastAPI SDK
- **Frontend**: React Hooks SDK (Phase 2b)
- **DB**: PostgreSQL + RLS

## フェーズ状況

| Phase | 内容 | 状態 |
|-------|------|------|
| 1 | Backend SDK基盤 (JWT, JWKS, RLS) | ✅ 完了 |
| 2a | Rate Limiting, MFA, SMTP | ✅ 完了 |
| 2b | Frontend SDK (React Hooks) | ✅ 完了 |
| 3 | ユーザー管理UI (Custom React + Admin API), Keycloak Themes | ✅ 完了 |
| 3.5 | テナントMFAポリシー管理 | ✅ 完了 |
| 4 | ユーザー招待フロー（招待制ユーザー登録） | 🔧 設計済み・実装待ち |

## 主要ADR

| ADR | 決定事項 |
|-----|---------|
| 001 | Keycloak採用（OSS、OIDC準拠、Docker対応）|
| 002 | Authorization Code Flow + PKCE |
| 003 | **SaaS BtoB: Shared Realm + Groups + User Attribute**（旧: Realm per tenant） |
| 004 | PyJWT + 独自JWKSService（graceful degradation）|
| 005 | oidc-client-ts + React Hooks wrapper |
| 006 | Defense in Depth: Middleware + RLS |
| 007 | Fixed-window Rate Limiting + InMemory Store |
| 008 | Frontend SDK: AuthProvider + useAuth + AuthGuard |
| 009 | Keycloak内蔵SMTP（ポータビリティ優先）|
| 010 | ユーザー管理UI: **カスタムReact + Backend Admin API**（Keycloak委譲から変更） |
| 011 | ロールベースアクセス制御（Keycloakロール + JWTクレーム）|

## Backend SDK構成

```
packages/backend-sdk/src/common_auth/
├── config.py          # AuthConfig (env読み込み)
├── setup.py           # setup_auth() FastAPI統合
├── middleware/
│   ├── jwt_auth.py    # JWT検証
│   ├── rate_limit.py  # Rate Limiting (Fixed-window counter)
│   ├── tenant.py      # RLS SET LOCAL
│   └── security_headers.py
├── services/jwks.py   # JWKS取得・キャッシュ
├── dependencies/      # FastAPI DI
└── routers/
    ├── auth.py        # /auth/health, /auth/me, /auth/logout, /auth/mfa-status
    └── admin.py       # /api/admin/users (CRUD), /api/admin/security/mfa, /api/admin/clients
```

## 設定項目

```env
# 必須
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=common-auth
KEYCLOAK_CLIENT_ID=backend-app

# テナント識別（SaaS BtoB: custom推奨）
TENANT_ID_SOURCE=custom        # custom | iss | fixed
TENANT_ID_CLAIM=tenant_id      # TENANT_ID_SOURCE=custom 時に必須

# オプション
JWKS_CACHE_TTL=86400
ENABLE_RLS=true
ENABLE_USER_SYNC=false
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=60
RATE_LIMIT_DEFAULT_WINDOW=60
RATE_LIMIT_LOGIN_REQUESTS=5
RATE_LIMIT_LOGIN_WINDOW=60
RATE_LIMIT_TRUSTED_PROXIES=

# Admin API（ユーザー管理用、任意）
KC_ADMIN_CLIENT_ID=admin-api-client
KC_ADMIN_CLIENT_SECRET=<secret>
```

## テスト状況

- 単体テスト: 39件 (100% pass)
- カバレッジ: 78%
- 主要コンポーネント: 85%以上

## Frontend SDK構成

```
packages/frontend-sdk/src/
├── index.ts           # エクスポート
├── types.ts           # 型定義
├── AuthContext.ts     # React Context
├── AuthProvider.tsx   # Provider + UserManager
│                      # ⚠️ extractRealmRoles() はアクセストークン優先で読む
│                      #    (Keycloak が ID token にロールを含めない設定の場合の防衛)
├── useAuth.ts         # Main Hook
├── AuthGuard.tsx      # Route Guard
└── *.test.tsx         # テスト (8件)
```

## Example App 構成

```
examples/react-app/
├── package.json       # predev: SDK自動ビルド + Viteキャッシュクリア
├── src/
│   ├── pages/Dashboard.tsx    # SideNav付きアプリシェル
│   ├── pages/AdminUsers.tsx   # 管理画面 (CRUD + MFAリセット)
│   └── api/adminApi.ts        # Backend Admin API クライアント

examples/fastapi-app/
└── main.py            # FastAPI + Backend SDK (port 8000)
```

## Keycloak 設定の注意点

```
auth-stack/keycloak/
├── realm-export.json
│   ├── smtpServer.host = "mailhog"  ← #{SMTP_HOST} プレースホルダーではない
│   └── roles scope mappers
│       ├── realm roles: id.token.claim = "true"  ← 必須
│       └── client roles: id.token.claim = "true" ← 必須
└── themes/common-auth/login/theme.properties
    └── import=common の行 ← 含めると500エラー発生 (削除済み)
```

⚠️ `docker-compose down -v` 後は CLAUDE.md の P1・P2 セルフチェックを実行すること。

## 次のタスク

Phase 3.5は完了済み。Phase 4（招待フロー）設計完了・実装待ち。

### Phase 4: ユーザー招待フロー（設計完了）

追加ファイル:
```
packages/backend-sdk/src/common_auth/
├── routers/invitation.py         # Public招待API (/api/invitations/*)
├── services/email_service.py     # SMTP直接送信サービス
└── dependencies/db.py            # db_pool / RLSバイパス接続の依存注入

examples/react-app/src/
├── pages/InviteUsers.tsx          # 招待発行画面 (/admin/users/invite)
├── pages/AdminInvitations.tsx     # 招待一覧管理 (/admin/invitations)
└── pages/InviteAccept.tsx         # 招待承諾画面 (/invite/accept?token=xxx, Public)

alembic/versions/xxx_add_invitation_tokens.py  # DBマイグレーション
```

追加環境変数:
```env
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=noreply@example.com
INVITATION_BASE_URL=http://localhost:5173
INVITATION_EXPIRES_HOURS=72
KEYCLOAK_PW_POLICY_HINT=8文字以上、英数字を含む必要があります
```

今後の拡張候補:
- 信頼済みデバイス（Cookie）MFAスキップの有効化
- メールOTPプロバイダーの実装
- E2Eテストの拡充
- 本番環境デプロイガイド

## 設計書一覧

### ドキュメント体系

```
docs/design/
├── *.md                    ← 正式な設計書（仕様・決定事項のみ）
├── auth/mfa/*.md           ← MFA関連の正式な設計書
└── logs/*.md               ← 会議ログ（議論の経緯・根拠追跡用）
```

> **参照ルール**: 実装時は正式な設計書のみを参照する。
> 会議ログは設計判断の根拠を追跡する必要がある場合にのみ参照する。

### コア設計書（正式）

| ファイル | 内容 | 元ログ |
|---------|------|--------|
| [architecture.md](design/architecture.md) | システムアーキテクチャ全体設計 | `logs/2026-03-01_163700_auth-module.md` |
| [multi-tenant.md](design/multi-tenant.md) | マルチテナント設計（Shared Realm + Groups） | `logs/2026-03-01_saas-multitenant.md` |
| [user-management.md](design/user-management.md) | Phase 3 ユーザー管理・RBAC | `logs/2026-03-01_phase3-user-management.md` |
| [backend-sdk-details.md](design/backend-sdk-details.md) | Backend SDK設計（Rate Limiting / SMTP含む） | `logs/2026-03-01_190131_phase2-features.md` |
| [frontend-sdk-details.md](design/frontend-sdk-details.md) | Frontend SDK設計 | `logs/2026-03-01_190131_phase2-features.md` |
| [react-example-app.md](design/react-example-app.md) | React Example App設計 | — |

### MFA設計書（正式: `docs/design/auth/mfa/`）

| ファイル | 内容 | 元ログ |
|---------|------|--------|
| [infrastructure.md](design/auth/mfa/infrastructure.md) | MFA基盤インフラ（Keycloak設定・環境変数） | `logs/design-001-mfa.md` |
| [tenant-policy.md](design/auth/mfa/tenant-policy.md) | テナントMFAポリシー管理 | `logs/design-002-tenant-mfa-policy.md` |
| [login-flow.md](design/auth/mfa/login-flow.md) | 統合MFA認証フロー | — |
| [account-settings.md](design/auth/mfa/account-settings.md) | アカウントMFA設定 | — |

---

*最終更新: 2026-04-04*
