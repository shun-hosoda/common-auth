# プロジェクトコンテキスト — common-auth

## 概要

Keycloak ベースのマルチテナント認証基盤。フロントエンド SDK / バックエンド SDK / Example App で構成。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| IdP | Keycloak 24（Docker） |
| Frontend SDK | TypeScript, oidc-client-ts v3.4.1, tsup |
| React Example App | React 18, Vite, Vitest + happy-dom |
| Backend SDK | Python, PyJWT |
| Backend Example | FastAPI, uvicorn |
| DB | PostgreSQL（Docker） |
| メール | MailHog（Docker, 開発用） |
| テスト | Jest + ts-jest（SDK）, Vitest（React App）, pytest（Backend SDK） |

## ディレクトリ構造

```
.
├── CLAUDE.md                     # AI エントリーポイント（汎用）
├── .claude/                      # 汎用 AI ルール・スキル
├── .ai-project/                  # ← このフォルダ（プロジェクト固有）
├── auth-stack/                   # Keycloak + DB の Docker Compose 環境
│   ├── docker-compose.yml
│   ├── keycloak/
│   │   ├── realm-export.json     # ★ Realm 設定（クライアント・フロー・SMTP）
│   │   └── themes/common-auth/   # カスタムテーマ
│   └── postgres/
│       ├── init.sql
│       └── add_invitation_tokens.sql
├── packages/
│   ├── frontend-sdk/             # @common-auth/react（npm パッケージ）
│   │   ├── src/
│   │   │   ├── AuthProvider.tsx  # 認証コンテキスト・ロール抽出
│   │   │   ├── Callback.tsx      # OIDC コールバック処理
│   │   │   ├── types.ts          # 型定義
│   │   │   └── index.ts          # エクスポート
│   │   └── tests/
│   └── backend-sdk/              # common-auth-sdk（PyPI パッケージ）
│       ├── src/common_auth/
│       └── tests/
├── examples/
│   ├── react-app/                # React Example App（Vite, port 3000）
│   │   ├── src/
│   │   │   ├── App.tsx           # ルーティング・認証ガード
│   │   │   └── components/       # UI コンポーネント
│   │   └── vite.config.ts        # Vite 設定（proxy → 8000）
│   └── fastapi-app/              # FastAPI Example App（port 8000）
│       ├── main.py
│       └── .env                  # ★ KC_ADMIN_* 等の環境変数
├── docs/                         # 設計書・ADR・API仕様
│   ├── _summary.md               # 全設計書の要約
│   ├── prd/prd.md
│   ├── adr/
│   ├── api/openapi.yaml
│   ├── db/schema.sql
│   ├── design/                   # 設計書
│   └── review/                   # レビュー設定・ログ
├── infra/                        # Docker Compose（TOTP テスト用等）
├── scripts/                      # 診断・修正スクリプト
└── tests/                        # E2E / Integration / Unit テスト
```

## 主要ポート

| サービス | ポート | 用途 |
|---------|--------|------|
| Keycloak | 8080 | IdP（認証・管理API） |
| FastAPI | 8000 | バックエンド API |
| React App | 3000 | フロントエンド |
| MailHog UI | 8025 | メール確認（開発用） |
| MailHog SMTP | 1025 | SMTP（Keycloak → MailHog） |
| PostgreSQL (Keycloak) | 5432 | Keycloak DB |
| PostgreSQL (App) | 5433 | アプリケーション DB |

## Keycloak 設定

- **Realm**: `common-auth`
- **クライアント**: `example-app`（public, PKCE）, `admin-api-client`（confidential, サービスアカウント）
- **認証フロー**: `unified-mfa-browser`（カスタム、conditional-user-attribute ベースの MFA ゲート）
- **SMTP**: MailHog（`mailhog:1025`）

## テストアカウント

| メールアドレス | パスワード | ロール |
|--------------|-----------|-------|
| `admin_acme-corp@example.com` | `admin123` | `tenant_admin` |
| `user_acme-corp@example.com` | `user123` | `tenant_user` |
