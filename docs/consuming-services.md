# common-auth 利用ガイド（サービス開発者向け）

このドキュメントは `common-auth` を利用する新規サービスの開発者向けです。

## 構成方針

| レイヤー | 方針 |
|---------|------|
| **バックエンド (Python)** | `common-auth` パッケージを GitHub Releases から pip install |
| **フロントエンド** | 各サービスで独自実装。`examples/react-app` をベースにコピーして改造するのが最速 |

---

## 1. バックエンド (Python / FastAPI)

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
