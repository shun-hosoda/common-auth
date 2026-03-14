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
| 3 | ユーザー管理UI (Custom React + Admin API), Keycloak Themes | 🚧 設計中 |

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
│   ├── rate_limit.py  # Rate Limiting
│   ├── tenant.py      # RLS SET LOCAL
│   └── security_headers.py
├── services/jwks.py   # JWKS取得・キャッシュ
├── dependencies/      # FastAPI DI
└── routers/auth.py    # /auth/health, /auth/me
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
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=60
RATE_LIMIT_LOGIN_REQUESTS=5
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
├── useAuth.ts         # Main Hook
├── AuthGuard.tsx      # Route Guard
└── *.test.tsx         # テスト (8件)
```

## 次のタスク

Phase 3: ユーザー管理 + Keycloak Themes
1. Backend Admin API（Keycloak Admin REST APIプロキシ）
2. Reactユーザー管理画面
3. Keycloakログインテーマ（CSS変数ベース）
4. テナント境界チェック強化

---

*最終更新: 2026-03-01*
