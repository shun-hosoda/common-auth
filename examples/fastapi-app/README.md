# FastAPI Example App（common-auth SDK）

common-auth SDKの使用例を示すFastAPIアプリケーション。  
**URL**: http://127.0.0.1:8000 / **Swagger UI**: http://127.0.0.1:8000/docs

---

## 起動手順（初回）

### Step 1 — Auth Stack を起動（Keycloak・DB）

```powershell
cd auth-stack
copy .env.example .env   # 初回のみ
docker-compose up -d
```

> Keycloak の起動確認: ブラウザで http://127.0.0.1:8080 が開けばOK（1〜2分かかります）
> ※ Windows では `localhost` が IPv6 に解決されタイムアウトする場合があります。`127.0.0.1` を使ってください。

### Step 2 — 環境変数ファイルを作成

```powershell
cd examples/fastapi-app
copy .env.example .env   # 初回のみ
```

> デフォルト設定のままでローカル Auth Stack に接続できます。変更不要。

### Step 3 — SDK をインストール

```powershell
pip install -e ../../packages/backend-sdk
```

### Step 4 — 起動

```powershell
uvicorn main:app --reload
```

http://127.0.0.1:8000 で起動します。

---

## 2回目以降の起動

```powershell
# Auth Stack が止まっている場合のみ
cd auth-stack
docker-compose up -d

# FastAPI 起動
cd examples/fastapi-app
uvicorn main:app --reload
```

---

## API エンドポイント

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| GET | `/` | 不要 | ヘルスチェック |
| GET | `/docs` | 不要 | Swagger UI |
| GET | `/auth/health` | 不要 | Keycloak 接続確認 |
| GET | `/api/me` | JWT必須 | 自分のユーザー情報 |
| GET | `/api/protected` | JWT必須 | 認証確認用 |
| GET | `/api/admin` | admin role | 管理者専用 |
| GET | `/api/admin/users` | tenant_admin role | ユーザー一覧 |

---

## 動作確認（テスト用トークンの取得）

### PowerShell

```powershell
$res = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8080/realms/common-auth/protocol/openid-connect/token" `
  -Body @{
    grant_type = "password"
    client_id  = "example-app"
    username   = "testuser_acme-corp@example.com"
    password   = "password123"
  }
$TOKEN = $res.access_token

# API呼び出し
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/me" `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

### curl（bash / WSL）

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/realms/common-auth/protocol/openid-connect/token \
  -d "grant_type=password&client_id=example-app&username=testuser_acme-corp%40example.com&password=password123" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://127.0.0.1:8000/api/me -H "Authorization: Bearer $TOKEN"
```

---

## トラブルシューティング

### 「ModuleNotFoundError」が出る

```powershell
pip install -e ../../packages/backend-sdk
```

### 「Unable to get JWKS」エラー

Keycloak が起動していない、または `localhost` が IPv6 に解決されている。

```powershell
# 起動確認（127.0.0.1 を使うこと）
Invoke-WebRequest http://127.0.0.1:8080 -UseBasicParsing | Select-Object StatusCode

# 起動していない場合
cd auth-stack
docker-compose up -d
```

> **Windows の注意**: ブラウザや curl で `localhost:8080` がタイムアウトする場合は `127.0.0.1:8080` を使ってください。

### 「App DB connection failed」警告

app-db コンテナの状態を確認:

```powershell
docker ps --filter name=app-db
```

> この警告はユーザーグループ機能が無効になるだけで、それ以外の API は正常に動作します。

### 「Invalid token」エラー

- トークンの有効期限切れ（デフォルト: 5分）→ 再取得してください
- `KEYCLOAK_CLIENT_ID` が `.env` で `example-app` になっていることを確認

---

## 環境変数（.env）の主要項目

| 変数 | デフォルト値 | 説明 |
|------|------------|------|
| `KEYCLOAK_URL` | `http://127.0.0.1:8080` | Keycloak の URL（Windows は `localhost` 非推奨） |
| `KEYCLOAK_REALM` | `common-auth` | Realm 名 |
| `KEYCLOAK_CLIENT_ID` | `example-app` | クライアント ID |
| `KC_ADMIN_CLIENT_SECRET` | `admin-api-client-secret` | 管理API用シークレット |
| `APP_DATABASE_URL` | （未設定） | asyncpg 接続先（ユーザーグループ機能用） |
