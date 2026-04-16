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
- `super_admin@example.com` / `superadmin123` (super_admin role, 全テナント管理者)
- `testuser_acme-corp@example.com` / `password123` (user role, acme-corp)
- `admin_acme-corp@example.com` / `admin123` (tenant_admin role, acme-corp)
- `testuser_globex-inc@example.com` / `password123` (user role, globex-inc)
- `admin_globex-inc@example.com` / `admin123` (tenant_admin role, globex-inc)

> **大量テストユーザー（100件×2テナント）の作成:** `scripts/seed-test-users.ps1` を実行してください。  
> 詳細は [docs/test-users.md](../docs/test-users.md) を参照。

**クライアントの使い分け:**
- **フロントエンドアプリ**: `example-app`を使用（React App）
- **バックエンドアプリ**: `backend-app`を使用（FastAPI App）

## サービス一覧

| サービス | ポート | 説明 |
|---|---|---|
| Keycloak | 8080 | Identity Provider |
| Keycloak DB | (内部) | Keycloak用PostgreSQL |
| App DB | 5433 | アプリケーション用PostgreSQL (test/dev) |
| **MailHog** | **8025** | **ローカル開発用ダミーメールサーバー (Web UI)** |
| **MailHog** | **1025** | **SMTP受信ポート** |

## アプリケーションデータベース

`app-db` サービスは、テスト用のPostgreSQLインスタンスを提供します：
- 事前作成テーブル: `tenants`, `user_profiles`, `tenant_groups`, `user_group_memberships`, `permissions`, `group_permissions`, `user_permissions`
- Row-Level Security有効化（全テーブル）
- サンプルテナント: `common-auth` / `acme-corp` / `globex-inc`

**テストグループ（初期データ）:**

| テナント | グループ | 付与権限 |
|----------|---------|---------|
| acme-corp | 管理部 | 全権限 |
| acme-corp | 開発チーム | users/reports 参照のみ |
| acme-corp | 営業部 | （権限なし） |
| globex-inc | 管理部 | 全権限 |
| globex-inc | 開発チーム | users/reports 参照のみ |
| globex-inc | 営業部 | （権限なし） |

**ユーザー⇔グループ紐付け:**
- `admin_acme-corp@example.com` → 管理部（acme-corp）
- `testuser_acme-corp@example.com` → 開発チーム（acme-corp）
- `admin_globex-inc@example.com` → 管理部（globex-inc）
- `testuser_globex-inc@example.com` → 営業部（globex-inc）

> **注意**: ユーザー⇔グループの紐付けは `user_profiles` が Keycloak ログイン時に同期されるタイミングで自動実行されます（`trg_auto_assign_test_groups` トリガー）。各ユーザーが一度ログインすると即時にグループへ追加されます。

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

ローカル開発環境では **MailHog**（ダミーメールサーバー）が自動起動され、Keycloakのメール送信先に設定されています。
`.env.example` のデフォルト値のまま、追加設定なしで動作します。

```
Keycloak → mailhog:1025 (SMTP)
           → http://localhost:8025 (Web UI で受信メールを確認)
```

**メール確認手順:**
1. `docker-compose up -d` で起動
2. http://localhost:8025 をブラウザで開く
3. パスワードリセットやメール認証を実行→ MailHogに送信メールが表示される

**本番環境で実SMTPに切り替える場合は、`.env` で変更:**

```bash
# Gmail例
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_AUTH=true
SMTP_STARTTLS=true
# (Gmailの場合は2段階認証 + アプリパスワードの発行が必要)
```

### MFA (TOTP)

MFAは `realm-export.json` でTOTP（6桁、30秒）として事前設定されています。
ユーザーはKeycloakアカウントコンソール（`http://localhost:8080/realms/common-auth/account/`）
から任意でMFAを登録できます。

全ユーザーにMFAを**必須化**するには、Keycloak管理コンソールで
`CONFIGURE_TOTP` をデフォルトの必須アクションとして設定してください。

### ユーザー自己登録

自己登録はデフォルトで無効化されています（`registrationAllowed: false`）。
運用上必要な場合のみ、Keycloak管理コンソールで有効化してください。

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
