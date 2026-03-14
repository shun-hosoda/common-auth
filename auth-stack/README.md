# Auth Stack

Keycloak + PostgreSQL Docker Compose構成。common-authの開発・テスト用環境。

## クイックスタート

### 1. 環境変数のコピー

```bash
cp .env.example .env
```

必要に応じて `.env` のポートや認証情報を編集してください。

### 2. サービス起動

```bash
docker-compose up -d
```

### 3. 初期セットアップ

Auth Stackを起動すると、`common-auth` Realmが自動的にインポートされます。

**注意**: 初回起動時またはRealmを再インポートする場合は、コンテナとボリュームを削除してください：

```bash
docker-compose down -v
docker-compose up -d
```

### 4. Keycloak管理コンソールへアクセス

- URL: http://localhost:8080
- ユーザー名: `admin`
- パスワード: `admin`

### 5. Realmインポートの確認

`common-auth` Realmが自動的にインポートされ、以下が含まれています：

**クライアント:**
- `backend-app`: Backend SDK用（Confidential Client）
  - FastAPI、Django、Expressなどのサーバーサイドアプリケーション用
  - クライアントシークレットを使用してKeycloakと認証
  - JWT検証、Admin API操作に使用
- `example-app`: Frontend Example用（Public Client）
  - React、Vue、Angularなどのブラウザアプリケーション用
  - PKCE使用、シークレット不要
  - ブラウザで直接Keycloakと通信

**テストユーザー:**
- `testuser_acme-corp@example.com` / `password123` (user role, acme-corp)
- `admin_acme-corp@example.com` / `admin123` (tenant_admin role, acme-corp)
- `testuser_globex-inc@example.com` / `password123` (user role, globex-inc)
- `admin_globex-inc@example.com` / `admin123` (tenant_admin role, globex-inc)

> **super_admin ロールについて**: `super_admin` ロールはRealm定義に存在しますが、デフォルトでは割り当てユーザーがいません。Keycloak管理コンソール全体を操作するテストが必要な場合は、Keycloak管理コンソール（`admin` / `admin`）から手動でユーザーにロールを付与してください。

**クライアントの使い分け:**
- **フロントエンドアプリ**: `example-app`を使用（React App）
- **バックエンドアプリ**: `backend-app`を使用（FastAPI App）

## サービス一覧

| サービス | ポート | 説明 |
|---|---|---|
| Keycloak | 8080 | Identity Provider |
| Keycloak DB | (内部) | Keycloak用PostgreSQL |
| App DB | 5433 | アプリケーション用PostgreSQL (test/dev) |

## アプリケーションデータベース

`app-db` サービスは、テスト用のPostgreSQLインスタンスを提供します：
- 事前作成テーブル: `tenants`, `user_profiles`
- Row-Level Security有効化
- サンプルテナント: `common-auth`

接続方法:
```bash
psql -h localhost -p 5433 -U app_user -d app_db
```

## ヘルスチェック

```bash
# Keycloak
curl http://localhost:8080/health/ready

# App DB
docker-compose exec app-db pg_isready -U app_user
```

## サービス停止

```bash
docker-compose down

# ボリューム削除（データベースリセット）
docker-compose down -v
```

## トラブルシューティング

### Keycloakの起動に時間がかかる

初回起動は1-2分かかります。ログを確認：
```bash
docker-compose logs -f keycloak
```

### Realmがインポートされない

`keycloak/realm-export.json` の存在を確認し、ログをチェック：
```bash
docker-compose logs keycloak | grep -i import
```

### ポート競合

`.env` でポート番号を変更：
```bash
KEYCLOAK_PORT=9080
APP_DB_PORT=5434
```

### frontend-appクライアントが見つからない

Realmが正しくインポートされているか確認してください。
再インポートが必要な場合：

```bash
docker-compose down -v
docker-compose up -d
```

数分待ってKeycloakが完全に起動したら、http://localhost:8080 で `example-app` クライアントが存在することを確認してください。

## Phase 2機能

### SMTP / メール

パスワードリセットやメール認証にはSMTP設定が必要です。
`.env` で `SMTP_*` 変数を設定してください。

SMTP未設定の場合でもKeycloakは起動しますが、メール依存機能
（パスワードリセット、メール認証）は失敗します。

### MFA (TOTP)

MFAは `realm-export.json` でTOTP（6桁、30秒）として事前設定されています。
ユーザーはKeycloakアカウントコンソール（`http://localhost:8080/realms/common-auth/account/`）
から任意でMFAを登録できます。

全ユーザーにMFAを**必須化**するには、Keycloak管理コンソールで
`CONFIGURE_TOTP` をデフォルトの必須アクションとして設定してください。

### ユーザー自己登録

自己登録はデフォルトで有効化されています（`registrationAllowed: true`）。
ユーザーはKeycloakログインページから登録できます。

### レート制限

レート制限はBackend SDKミドルウェアで適用され、Keycloakではありません。
`.env` で制限を設定：

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=60    # 1分あたり
RATE_LIMIT_LOGIN_REQUESTS=5       # 1分あたり
```

## 開発ワークフロー

1. Auth Stack起動: `docker-compose up -d`
2. Keycloakの起動完了を待つ（1-2分）
3. Backend SDKでホットリロード開発
4. 起動中のKeycloakでテスト
5. 停止: `docker-compose down`

## 本番デプロイ

このDocker Compose構成は**開発/テスト専用**です。

本番環境では：
- マネージドKeycloak（Kubernetes上のKeycloak Operatorなど）を使用
- マネージドPostgreSQL（AWS RDS、Google Cloud SQLなど）を使用
- 適切なシークレット管理を設定
- 有効な証明書でHTTPSを有効化
- セキュリティ設定を確認・強化

本番デプロイガイドラインについては `docs/` を参照してください。
