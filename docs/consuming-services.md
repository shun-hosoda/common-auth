# common-auth 利用ガイド（サービス開発者向け）

このドキュメントは `common-auth` を利用する新規サービスの開発者向けです。

---

## 1. 事前準備: GitHub Personal Access Token (PAT) の取得

GitHub Packages からパッケージをインストールするために PAT が必要です。

1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (fine-grained)**
2. 必要な権限: `read:packages`
3. 取得したトークンを安全な場所に保管する

---

## 2. Python サービス（FastAPI）での利用

### インストール

```bash
# requirements.txt または pyproject.toml に追記
# GitHub Releases から直接 wheel をインストール

pip install "common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl"
```

> `ORG/REPO` は実際のリポジトリパスに置き換えてください。

#### pyproject.toml に固定する場合

```toml
[project]
dependencies = [
    "common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl",
]
```

#### requirements.txt に固定する場合

```
common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl
```

### 最小実装 (FastAPI)

```python
# main.py
import os
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

config = AuthConfig.from_env()
setup_auth(app, config, db_dsn=os.environ.get("APP_DATABASE_URL"))

@app.get("/api/private")
async def private(user: AuthUser = Depends(get_current_user)):
    return {"user": user.email, "tenant": user.tenant_id}
```

### 必要な環境変数 (.env)

```env
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=common-auth
KEYCLOAK_CLIENT_ID=your-service-client
KC_ADMIN_CLIENT_ID=admin-api-client
KC_ADMIN_CLIENT_SECRET=your-secret
APP_DATABASE_URL=postgresql://user:pass@localhost:5433/app_db  # グループ機能を使う場合
```

---

## 3. TypeScript/React サービスでの利用

### GitHub Packages npm registry の設定

プロジェクトルートに `.npmrc` を作成：

```
@common-auth:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

環境変数を設定：

```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # あなたの PAT

# .env ファイル (gitignore に追加すること)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### インストール

```bash
npm install @common-auth/react@1.0.0
```

### 最小実装 (React)

```tsx
// main.tsx
import { AuthProvider } from '@common-auth/react'

const authConfig = {
  authority: 'http://localhost:8080/realms/common-auth',
  client_id: 'your-service-client',
  redirect_uri: `${window.location.origin}/callback`,
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <AuthProvider config={authConfig}>
    <App />
  </AuthProvider>
)
```

```tsx
// 保護されたコンポーネント
import { useAuth, AuthGuard } from '@common-auth/react'

function Dashboard() {
  const { user } = useAuth()
  return <div>こんにちは {user?.profile.email}</div>
}

// 認証必須ページ
export default function ProtectedPage() {
  return (
    <AuthGuard>
      <Dashboard />
    </AuthGuard>
  )
}
```

---

## 4. バージョンアップ方法

### Python サービス

```bash
# requirements.txt の URL を新バージョンに書き換えて再インストール
pip install "common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.1/common_auth-1.0.1-py3-none-any.whl"
```

### TypeScript サービス

```bash
npm install @common-auth/react@1.0.1
```

---

## 5. バージョン選定の指針

| バージョン変化 | 意味 | 対応方法 |
|-------------|------|---------|
| パッチ `1.0.x` | バグ修正のみ、後方互換 | すぐにアップデート推奨 |
| マイナー `1.x.0` | 新機能追加、後方互換 | 任意のタイミングでアップデート |
| メジャー `x.0.0` | 破壊的変更あり | CHANGELOG を確認してから対応 |

---

## 6. リリース一覧の確認

https://github.com/ORG/REPO/releases

---

## 7. 問題が発生した場合

1. [Issues](https://github.com/shun-hosoda/common-auth/issues) に報告
2. `common-auth` リポジトリで修正・テスト
3. `.\scripts\release.ps1 -Version 1.x.x -Message "fix: ..."` でリリース
4. 各サービスでバージョンアップ

---

## 8. Keycloak インフラの共有

各サービスは同一の Keycloak インスタンスとレルムを利用します。  
新規サービスで必要なクライアントを追加する場合は、インフラ担当者に依頼してください。

**共有インフラ:**
- Keycloak: `http://keycloak.internal:8080` (本番)
- realm: `common-auth` (マルチテナント対応済み)
- DB (PostgreSQL): グループ・権限データを共有
