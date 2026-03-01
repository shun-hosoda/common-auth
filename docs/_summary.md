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
| 2b | Frontend SDK (React Hooks) | ⏳ 未着手 |
| 3 | Redis対応, 高度な機能 | 📋 計画のみ |

## 主要ADR

| ADR | 決定事項 |
|-----|---------|
| 001 | Keycloak採用（OSS、OIDC準拠、Docker対応）|
| 002 | Authorization Code Flow + PKCE |
| 003 | Realm単位のマルチテナント分離 |
| 004 | PyJWT + 独自JWKSService（graceful degradation）|
| 005 | oidc-client-ts + React Hooks wrapper |
| 006 | Defense in Depth: Middleware + RLS |
| 007 | Fixed-window Rate Limiting + InMemory Store |
| 008 | Frontend SDK: AuthProvider + useAuth + AuthGuard |
| 009 | Keycloak内蔵SMTP（ポータビリティ優先）|

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

# オプション
TENANT_ID_SOURCE=iss|custom|fixed
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

## 次のタスク

Phase 2b: Frontend SDK
1. `packages/frontend-sdk/` 作成
2. AuthProvider, useAuth, AuthGuard実装
3. Example React App
4. 単体テスト (Jest + RTL)

---

*最終更新: 2026-03-01*
