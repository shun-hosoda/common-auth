# common-auth Backend SDK

KeycloakとOIDCベースのポータブル認証SDK（FastAPIアプリケーション向け）

## 機能

- **OIDC Authorization Code Flow + PKCE**: OAuth 2.1推奨フロー
- **JWT検証**: JWKS キャッシュによるRS256署名検証
- **マルチテナント対応**: PostgreSQLのRow-Level Security (RLS)
- **セキュリティヘッダー**: HSTS、CSP、X-Frame-Optionsなど
- **グレースフルデグラデーション**: Keycloakダウン時もキャッシュされたJWKSで認証継続
- **開発者フレンドリー**: シンプルな `setup_auth(app, config)` 統合

## インストール

```bash
pip install common-auth
```

## クイックスタート

### 1. 環境変数の設定

```bash
export KEYCLOAK_URL=https://keycloak.example.com
export KEYCLOAK_REALM=my-tenant
export KEYCLOAK_CLIENT_ID=my-app
```

### 2. FastAPIとの統合

```python
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

# 認証のセットアップ
config = AuthConfig.from_env()
setup_auth(app, config)

@app.get("/api/protected")
async def protected_endpoint(user: AuthUser = Depends(get_current_user)):
    return {"user_id": user.sub, "tenant": user.tenant_id}
```

### 3. アプリの実行

```bash
uvicorn main:app --reload
```

## 設定

### 必須環境変数

| 変数 | 説明 |
|---|---|
| `KEYCLOAK_URL` | KeycloakのベースURL |
| `KEYCLOAK_REALM` | Realm名 |
| `KEYCLOAK_CLIENT_ID` | クライアントID |

### オプション環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `JWKS_CACHE_TTL` | 3600 | JWKS キャッシュのTTL（秒） |
| `DB_URL` | None | マルチテナント用のPostgreSQL URL |
| `TENANT_ID_CLAIM` | tenant_id | JWTのテナントIDクレーム名 |

### レート制限設定（Phase 2）

| 変数 | デフォルト | 説明 |
|---|---|---|
| `RATE_LIMIT_ENABLED` | true | レート制限の有効/無効 |
| `RATE_LIMIT_DEFAULT_REQUESTS` | 60 | デフォルトのリクエスト数制限（1分あたり） |
| `RATE_LIMIT_LOGIN_REQUESTS` | 5 | ログインエンドポイントの制限（1分あたり） |
| `RATE_LIMIT_TRUSTED_PROXIES` | [] | 信頼するプロキシのCIDRリスト |

## マルチテナント対応

### データベーススキーマ

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id TEXT NOT NULL,
    email TEXT NOT NULL
);

-- Row-Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON user_profiles
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

### 使用例

```python
from common_auth import get_db_session, AuthUser
from fastapi import Depends
from sqlalchemy.orm import Session

@app.get("/api/users")
async def get_users(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    # tenant_id が自動的にセットされ、RLS が適用される
    profiles = db.query(UserProfile).all()
    return profiles
```

## セキュリティ機能

### 自動適用されるヘッダー

- `Strict-Transport-Security`: HSTS有効化
- `Content-Security-Policy`: XSS対策
- `X-Frame-Options`: クリックジャッキング対策
- `X-Content-Type-Options`: MIMEスニッフィング対策
- `X-XSS-Protection`: XSSフィルター
- `Referrer-Policy`: リファラー制御

### レート制限（Phase 2）

```python
from common_auth import InMemoryRateLimitStore

# カスタムストレージでセットアップ
rate_limit_store = InMemoryRateLimitStore(max_size=10000)
setup_auth(app, config, rate_limit_store=rate_limit_store)
```

## 開発

### テストの実行

```bash
cd packages/backend-sdk
python -m pytest tests/ -v
```

### リンター

```bash
ruff check .
mypy src/
```

## ライセンス

MIT
