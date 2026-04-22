# common-auth 利用ガイド（サービス開発者向け）

新規サービスを `common-auth` に接続するための手順書です。

---

## 全体像

```
【共有インフラ（1回だけ構築済み）】
  Keycloak + PostgreSQL (auth-stack)
        ↕ 接続
【各サービス】
  バックエンド: common-auth パッケージ（pip）を使う
  フロントエンド: @common-auth/react パッケージ（npm）を使う
```

---

## STEP 0: 初回のみ — GitHub 設定（インフラ担当者が実施）

### 0-1. GitHub Actions のパーミッション設定

`https://github.com/shun-hosoda/common-auth` →
**Settings → Actions → General → Workflow permissions**
→ `Read and write permissions` を選択して Save

### 0-2. 初回リリースを実行して パッケージを公開する

```powershell
cd C:\Work_Private\01_Project\28_common-auth\common-auth
.\scripts\release.ps1 -Version 1.0.0 -Message "initial release"
```

数分後に GitHub Actions が完了すると以下が利用可能になります：
- `https://github.com/shun-hosoda/common-auth/releases` に wheel ファイル
- `https://github.com/orgs/shun-hosoda/packages` に `@common-auth/react` npm パッケージ

---

## STEP 1: Keycloak にクライアントを登録（サービスごとに1回）

新サービスを Keycloak に認識させるため、`realm-export.json` にクライアントを追加してインポートするか、Keycloak 管理画面から手動で登録します。

**最低限必要な設定:**

| 項目 | 値 |
|------|---|
| Client ID | `my-new-service`（任意） |
| Client authentication | OFF（パブリッククライアント） |
| Valid redirect URIs | `http://localhost:5173/*`（開発用） |
| Web origins | `http://localhost:5173` |

---

## STEP 2: バックエンド（Python / FastAPI）のセットアップ

### 2-1. パッケージのインストール

`requirements.txt` に追加：

```
common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-dotenv>=1.0.0
```

```bash
pip install -r requirements.txt
```

### 2-2. 環境変数 (.env)

```env
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=common-auth
KEYCLOAK_CLIENT_ID=my-new-service
KC_ADMIN_CLIENT_ID=admin-api-client
KC_ADMIN_CLIENT_SECRET=（インフラ担当者から取得）
APP_DATABASE_URL=postgresql://appuser:apppass@localhost:5433/app_db  # グループ機能を使う場合
```

### 2-3. main.py の実装

```python
import os
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

config = AuthConfig.from_env()
setup_auth(app, config, db_dsn=os.environ.get("APP_DATABASE_URL"))

# 認証が必要なエンドポイントの例
@app.get("/api/items")
async def list_items(user: AuthUser = Depends(get_current_user)):
    return {"tenant": user.tenant_id, "user": user.email}
```

これだけで以下のエンドポイントが**自動的に**追加されます：

| エンドポイント | 説明 |
|-------------|------|
| `GET /auth/health` | ヘルスチェック（認証不要） |
| `GET /auth/me` | ログインユーザー情報 |
| `GET /api/admin/users` | テナントユーザー管理 |
| `GET /api/admin/groups` | グループ管理 |
| `GET /api/admin/audit/logs` | 監査ログ |
| `GET /api/admin/security/mfa` | MFA ポリシー |

### 2-4. 起動確認

```bash
uvicorn main:app --reload
# → http://localhost:8000/auth/health で動作確認
```

---

## STEP 3: フロントエンド（React / TypeScript）のセットアップ

### 3-1. GitHub Packages の認証設定（開発者ごとに1回）

**Personal Access Token を取得：**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. `read:packages` にチェックを入れて生成
3. 生成されたトークンをメモしておく

**プロジェクトルートに `.npmrc` を作成：**

```
@common-auth:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=ghp_xxxxxxxxxxxx
```

> ⚠️ `.npmrc` は `.gitignore` に追加してコミットしないこと

### 3-2. プロジェクト作成とパッケージのインストール

```bash
# Vite で React プロジェクトを新規作成
npm create vite@latest my-frontend -- --template react-ts
cd my-frontend

# common-auth の React SDK をインストール
npm install @common-auth/react oidc-client-ts react-router-dom
```

### 3-3. 認証設定 (src/auth/config.ts)

```ts
export const authConfig = {
  authority: import.meta.env.VITE_KEYCLOAK_URL + '/realms/' + import.meta.env.VITE_KEYCLOAK_REALM,
  client_id: import.meta.env.VITE_CLIENT_ID,
  redirect_uri: window.location.origin + '/callback',
  post_logout_redirect_uri: window.location.origin,
  scope: 'openid profile email',
}
```

**.env:**
```env
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=common-auth
VITE_CLIENT_ID=my-new-service
```

### 3-4. main.tsx に AuthProvider を追加

```tsx
import { AuthProvider } from '@common-auth/react'
import { authConfig } from './auth/config'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <AuthProvider config={authConfig}>
    <App />
  </AuthProvider>
)
```

### 3-5. コールバックページ (src/pages/Callback.tsx)

```tsx
import { useEffect } from 'react'
import { useAuth } from '@common-auth/react'
import { useNavigate } from 'react-router-dom'

export function Callback() {
  const { handleCallback } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    handleCallback().then(() => navigate('/'))
  }, [])

  return <div>認証処理中...</div>
}
```

### 3-6. 認証が必要な画面の実装

```tsx
import { useAuth } from '@common-auth/react'

export function MyPage() {
  const { user, accessToken, logout } = useAuth()

  // API 呼び出し
  const fetchData = async () => {
    const res = await fetch('/api/items', {
      headers: { Authorization: `Bearer ${accessToken}` }
    })
    return res.json()
  }

  return (
    <div>
      <p>ようこそ {user?.profile.email}</p>
      <button onClick={() => logout()}>ログアウト</button>
    </div>
  )
}
```

> **より完全な実装例** → `examples/react-app/` を参照（管理画面・ナビゲーション等のUIコンポーネントあり）

---

## STEP 4: ローカル開発環境の起動

```bash
# 1. 共有インフラを起動（common-authリポジトリを clone して実行）
cd common-auth/auth-stack
docker-compose up -d

# 2. バックエンド起動
cd my-service/backend
uvicorn main:app --reload --port 8000

# 3. フロントエンド起動
cd my-service/frontend
npm run dev  # → http://localhost:5173
```

---

## STEP 5: バージョンアップ（SDK に修正があった場合）

### バックエンド

`requirements.txt` のバージョン番号を更新：

```
common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.1/common_auth-1.0.1-py3-none-any.whl
```

```bash
pip install -r requirements.txt
```

### フロントエンド

```bash
npm install @common-auth/react@1.0.1
```

---

## バージョン選定の指針

| 変化 | 意味 | 対応 |
|------|------|------|
| パッチ `1.0.x` | バグ修正・後方互換 | 即アップデート推奨 |
| マイナー `1.x.0` | 新機能追加・後方互換 | 任意のタイミング |
| メジャー `x.0.0` | 破壊的変更あり | CHANGELOG 確認後に対応 |

リリース一覧: https://github.com/shun-hosoda/common-auth/releases

---

## SDK の修正・リリース手順（インフラ担当者向け）

```powershell
# 1. common-auth リポジトリで修正・テスト後
.\scripts\release.ps1 -Version 1.0.1 -Message "fix: トークン検証の修正"

# → GitHub Actions が自動で:
#   ・backend-sdk wheel を GitHub Releases に添付
#   ・@common-auth/react を GitHub Packages に publish
```

---

## 問題が発生した場合

1. https://github.com/shun-hosoda/common-auth/issues に報告
2. `common-auth` リポジトリで修正・テスト・PR → main にマージ
3. `.\scripts\release.ps1` でリリース
4. 各サービスでバージョンアップ

### インストール

GitHub Releases の wheel を直接インストールします（PyPI 不要）。

**requirements.txt:**
```
common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl
```

**pyproject.toml:**
```toml
[project]
dependencies = [
    "common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.0/common_auth-1.0.0-py3-none-any.whl",
]
```

リリース一覧: https://github.com/shun-hosoda/common-auth/releases

### 最小実装

```python
# main.py
import os
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

config = AuthConfig.from_env()
setup_auth(app, config, db_dsn=os.environ.get("APP_DATABASE_URL"))

@app.get("/api/protected")
async def protected(user: AuthUser = Depends(get_current_user)):
    return {"user": user.email, "tenant": user.tenant_id, "roles": user.roles}
```

`setup_auth` を呼ぶだけで以下が自動登録されます:
- `GET /auth/health` — ヘルスチェック（認証不要）
- `GET /auth/me` — ログインユーザー情報
- `GET /api/admin/users` — テナントユーザー一覧（tenant_admin 必要）
- `GET /api/admin/groups` — グループ管理
- `GET /api/admin/audit/logs` — 監査ログ
- `GET /api/admin/security/mfa` — MFA ポリシー管理

### 必要な環境変数 (.env)

```env
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=common-auth
KEYCLOAK_CLIENT_ID=your-service-client
KC_ADMIN_CLIENT_ID=admin-api-client
KC_ADMIN_CLIENT_SECRET=your-admin-client-secret
APP_DATABASE_URL=postgresql://user:pass@localhost:5433/app_db  # グループ機能を使う場合のみ
```

### バージョンアップ

```
# requirements.txt の URL バージョン番号を更新して再インストール
pip install "common-auth @ https://github.com/shun-hosoda/common-auth/releases/download/v1.0.1/common_auth-1.0.1-py3-none-any.whl"
```

---

## 2. フロントエンド (React / TypeScript)

フロントは各サービスで独自実装します。
`examples/react-app` が完全なサンプルとして機能するので、コピーして改造するのが最速です。

### react-app をベースにする場合

```bash
# common-auth リポジトリから react-app をコピー
cp -r common-auth/examples/react-app my-new-service/frontend

cd my-new-service/frontend
npm install
```

**変更が必要な箇所:**

| ファイル | 変更内容 |
|---------|---------|
| `.env` | `VITE_KEYCLOAK_URL`, `VITE_CLIENT_ID` をサービスに合わせて変更 |
| `src/pages/` | 不要な管理画面を削除、サービス固有の画面を追加 |
| `src/api/` | バックエンドの API エンドポイントを変更 |

**そのまま使える認証ロジック:**
- `src/auth/` — OIDC 設定・コールバック処理
- `src/hooks/useAuth.ts` — ログイン/ログアウト/トークン管理
- `src/components/AuthGuard.tsx` — 認証必須ルートの保護

### 認証の基本パターン（コピー可）

```tsx
// ログインユーザー情報の取得
import { useAuth } from '../hooks/useAuth'

export function MyPage() {
  const { user, accessToken, logout } = useAuth()
  return (
    <div>
      <p>ようこそ {user?.profile.email}</p>
      <button onClick={() => logout()}>ログアウト</button>
    </div>
  )
}
```

```tsx
// API 呼び出し（Bearer トークンを付与）
const { accessToken } = useAuth()

const data = await fetch('/api/protected', {
  headers: { Authorization: `Bearer ${accessToken}` }
}).then(r => r.json())
```

---

## 3. バージョン選定の指針

| バージョン変化 | 意味 | 対応方法 |
|-------------|------|---------|
| パッチ `1.0.x` | バグ修正のみ、後方互換 | すぐにアップデート推奨 |
| マイナー `1.x.0` | 新機能追加、後方互換 | 任意のタイミングでアップデート |
| メジャー `x.0.0` | 破壊的変更あり | CHANGELOG を確認してから対応 |

---

## 4. 問題が発生した場合

1. [Issues](https://github.com/shun-hosoda/common-auth/issues) に報告
2. `common-auth` リポジトリで修正・テスト・PR
3. `.\scripts\release.ps1 -Version 1.x.x -Message "fix: ..."` でリリース
4. 各サービスの `requirements.txt` のバージョン番号を更新してデプロイ

---

## 5. Keycloak インフラ

各サービスは同一の Keycloak インスタンスを共有します。  
新規サービス用のクライアントが必要な場合はインフラ担当者に依頼してください。

- Keycloak: realm `common-auth`（マルチテナント対応済み）
- DB (PostgreSQL): グループ・権限データを共有
