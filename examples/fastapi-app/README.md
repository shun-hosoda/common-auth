# Common Auth Example Application - FastAPI

common-auth SDKの使用例を示すFastAPIアプリケーション。

## 前提条件

1. **Auth Stack（Keycloak）の起動**:
   ```bash
   cd ../../auth-stack
   cp .env.example .env
   docker-compose up -d
   ```

2. **Keycloakの起動完了を待つ**（1-2分）:
   ```bash
   curl http://localhost:8080
   ```

## セットアップ

### 1. 仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

必要に応じて `.env` を編集してください（デフォルトでローカルAuth Stackで動作します）。

**重要**: このFastAPI Appは`backend-app`（Confidential Client）を使用します。
- **フロントエンドアプリ**（React App）は`example-app`（Public Client）を使用
- **バックエンドアプリ**（FastAPI App）は`backend-app`（Confidential Client）を使用

## 実行

```bash
python main.py
```

またはuvicornで：
```bash
uvicorn main:app --reload
```

アプリケーションは http://localhost:8000 で起動します。

## API エンドポイント

### 公開エンドポイント

- `GET /`: ヘルスチェック
- `GET /docs`: Swagger UI（APIドキュメント）

### 保護されたエンドポイント（JWT必須）

- `GET /api/me`: 現在のユーザー情報を取得
- `GET /api/protected`: 保護されたエンドポイント（認証必須）
- `GET /api/admin`: 管理者専用エンドポイント（admin role必須）

## 認証テスト

### 1. アクセストークンの取得

**方法1**: React Appでログイン後、トークンをコピー
- http://localhost:3000 にアクセス
- ログイン: `testuser@example.com` / `password123`
- ダッシュボードでトークンをコピー

**方法2**: curlで直接取得（Direct Access Grants）
```bash
curl -X POST http://localhost:8080/realms/common-auth/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=backend-app" \
  -d "username=testuser@example.com" \
  -d "password=password123"
```

### 2. APIを呼び出す

```bash
# トークンを環境変数に設定
export TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# ユーザー情報を取得
curl http://localhost:8000/api/me \
  -H "Authorization: Bearer $TOKEN"

# 保護されたエンドポイントにアクセス
curl http://localhost:8000/api/protected \
  -H "Authorization: Bearer $TOKEN"
```

## マルチテナント対応（オプション）

### データベース接続

`DATABASE_URL`を設定してマルチテナント機能を有効化：

```bash
# .env
DATABASE_URL=postgresql+asyncpg://app_user:app_pass@localhost:5433/app_db
```

### テナント分離

Row-Level Security（RLS）により、各テナントのデータが自動的に分離されます：

```python
from common_auth import get_db_session, AuthUser
from fastapi import Depends
from sqlalchemy.orm import Session

@app.get("/api/users")
async def get_users(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    # user.tenant_id が自動的にセットされ、RLS が適用される
    users = db.query(UserProfile).all()  # 自分のテナントのデータのみ
    return users
```

## レート制限

Phase 2機能: リクエストレート制限がミドルウェアレベルで適用されます。

```bash
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=60    # 1分あたり
RATE_LIMIT_LOGIN_REQUESTS=5       # 1分あたり（ログインエンドポイント）
```

## トラブルシューティング

### "Unable to get JWKS" エラー

Keycloakが起動していることを確認：
```bash
curl http://localhost:8080
```

### "Invalid token" エラー

1. トークンの有効期限を確認（デフォルト: 5分）
2. `KEYCLOAK_URL`と`KEYCLOAK_REALM`が正しいか確認
3. トークンが正しいRealmから発行されているか確認

### データベース接続エラー

Auth Stackの`app-db`が起動していることを確認：
```bash
docker ps | grep app-db
```

## プロダクション対応

このExample Appは**開発/テスト用**です。本番環境では：

1. **環境変数の管理**: AWS Secrets Manager、HashiCorp Vaultなどを使用
2. **HTTPS**: リバースプロキシ（Nginx、Traefik）でHTTPSを終端
3. **レート制限**: Redisバックエンドでスケール可能なレート制限を実装
4. **ロギング**: 構造化ログ（JSON）とログ集約（ELK、Datadog）
5. **モニタリング**: Prometheus、Grafanaでメトリクス収集

詳細は `docs/` のプロダクションデプロイガイドを参照してください。
