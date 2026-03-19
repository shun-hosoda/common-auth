# サンプルアプリ 起動手順

ローカル開発環境における全コンポーネントの起動手順です。

## 構成

| コンポーネント | URL | 用途 |
|---|---|---|
| Keycloak | http://localhost:8080 | 認証サーバー（admin: `admin` / `admin`） |
| MailHog | http://localhost:8025 | メール確認 UI（ローカル SMTP） |
| FastAPI バックエンド | http://localhost:8000 | API サーバー（Swagger: `/docs`） |
| React フロントエンド | http://localhost:3000 | サンプル UI |

## 前提条件

- Docker Desktop が起動していること
- Python 3.10+ がインストールされていること
- Node.js 18+ がインストールされていること

---

## ステップ 1 — Docker Desktop を起動

Docker Desktop を起動し、デーモンが立ち上がるまで待ちます（15〜30 秒）。

---

## ステップ 2 — Auth Stack（Keycloak + DB）を起動

```powershell
cd auth-stack
docker compose up -d
```

> **初回のみ**: `.env.example` からコピーして `.env` を作成します。  
> デフォルト値のままでローカル動作します。
>
> ```powershell
> copy .env.example .env
> ```

Keycloak の起動確認（HTTP 200 が返れば OK）:

```powershell
Invoke-WebRequest -Uri "http://localhost:8080/realms/common-auth" -UseBasicParsing
```

---

## ステップ 3 — FastAPI バックエンドを起動

```powershell
# 初回のみ
cd examples\fastapi-app
copy .env.example .env
pip install -r requirements.txt

# 起動
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

バックグラウンドで起動する場合（PowerShell ジョブ）:

```powershell
Start-Job -ScriptBlock {
    Set-Location "C:\Work_Private\01_Project\28_common-auth\common-auth\examples\fastapi-app"
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
}
```

起動確認: http://localhost:8000/docs

---

## ステップ 4 — React フロントエンドを起動

```powershell
# 初回のみ
cd examples\react-app
copy .env.example .env
npm install

# 起動
npm run dev
```

バックグラウンドで起動する場合（PowerShell ジョブ）:

```powershell
Start-Job -ScriptBlock {
    Set-Location "C:\Work_Private\01_Project\28_common-auth\common-auth\examples\react-app"
    npm run dev
}
```

起動確認: http://localhost:3000

---

## テストユーザー

| ユーザー | パスワード | ロール |
|---|---|---|
| testuser@example.com | password123 | user |
| admin@example.com | password123 | tenant_admin |
| superadmin@example.com | password123 | super_admin |

---

## 停止手順

```powershell
# Docker コンテナを停止
cd auth-stack
docker compose down

# PowerShell バックグラウンドジョブを停止
Get-Job | Stop-Job
Get-Job | Remove-Job
```

データ（Keycloak DB）も含めて完全クリアする場合:

```powershell
docker compose down -v
```

---

## よくあるトラブル

| 症状 | 原因 | 対処 |
|---|---|---|
| `KEYCLOAK_URL is required` | `.env` ファイルが存在しない | `copy .env.example .env` を実行 |
| Docker コンテナが起動しない | Docker Desktop が未起動 | Docker Desktop を起動後に再実行 |
| Keycloak が `unhealthy` | Windows でのヘルスチェックシェル互換問題 | ログで `started in X.XXXs` が確認できれば正常 |
| フロントエンドが表示されない | Keycloak 未起動 | ステップ 2 を先に完了させる |
