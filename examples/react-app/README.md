# Common Auth - React サンプルアプリ

@common-auth/react SDKとKeycloakの統合を実演するReactアプリケーション。

## 機能

- OIDC Authorization Code + PKCEによるログイン
- 二要素認証（TOTP）
- パスワードリセット（メール通知）
- ユーザー自己登録
- ユーザープロフィールとトークン情報を表示するダッシュボード
- **ロールベースUI制御**: ロール（user / tenant_admin / super_admin）に応じて画面表示を切替
- **ユーザー管理**: tenant_admin以上のユーザーはKeycloak管理コンソールへのリンクを表示

## 前提条件

1. Auth Stackが起動していること（Keycloak + PostgreSQL）
2. Keycloakに`frontend-app`クライアントが登録されていること

## クイックスタート

### 1. Auth Stackの起動

```bash
cd ../../auth-stack
cp .env.example .env
docker-compose up -d
```

Keycloakの起動を待ちます（1-2分）：
```bash
curl http://localhost:8080/health/ready
```

### 2. Keycloakにクライアントが登録されていることを確認

`example-app` クライアントは `auth-stack` 起動時に自動的にインポートされます。

確認方法：
1. http://localhost:8080 を開く
2. `admin` / `admin` でログイン
3. "common-auth" Realmを選択
4. **Clients** を開いて `example-app` が存在することを確認

もし存在しない場合は、Auth Stackを再起動してRealmを再インポート：
```bash
cd ../../auth-stack
docker-compose down -v
docker-compose up -d
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集してKeycloak接続情報を設定します：

```env
VITE_KEYCLOAK_URL=http://localhost:8080   # Keycloak のベースURL（必須）
VITE_KEYCLOAK_REALM=common-auth           # Keycloak のRealm名（必須）
```

> **本番デプロイ時の注意**
> 
> `VITE_KEYCLOAK_URL` を本番KeycloakのURLに変更してください。
> 未設定の場合は `http://localhost:8080` がデフォルト値として使われます。
> 本番環境でlocalhost URLを含むビルドがデプロイされないよう注意してください。

### 4. インストール & 実行

```bash
npm install
npm run dev
```

http://localhost:3000 を開く

## テストユーザー

| ユーザー | パスワード | ロール | 利用できる機能 |
|----------|-----------|--------|----------------|
| `testuser@example.com` | `password123` | user | ダッシュボード、MFA設定 |
| `admin@example.com` | `admin123` | tenant_admin | ユーザー管理画面（Keycloak管理コンソールへのリンク） |
| `superadmin@example.com` | `superadmin123` | super_admin | ユーザー管理 + Keycloak管理コンソール（フル） |

## ログインフロー

1. **ログイン** をクリック → Keycloakログイン画面にリダイレクト
2. 認証情報を入力（上記テストユーザー参照）
3. （任意）MFA有効時はTOTPコードを入力
4. `/callback` → `/dashboard` にリダイレクトされる

## パスワードリセットフロー

1. **Forgot password?** をクリック → Keycloakリセット画面にリダイレクト
2. メールアドレスを入力
3. リセットリンクをメールで確認（SMTP設定が必要）
4. リンクをクリック → 新しいパスワードを設定
5. 新しいパスワードでログイン

## MFA設定フロー

1. ダッシュボードにログイン
2. **Setup MFA** をクリック → Keycloakアカウントコンソールにリダイレクト
3. 認証アプリ（Google Authenticator、Authyなど）でQRコードをスキャン
4. 認証コードを入力
5. 次回ログインからMFAが要求される

## ユーザー登録フロー

1. **Register** をクリック → Keycloak登録画面にリダイレクト
2. メール、パスワード、名前を入力
3. （メール認証有効時）メールで認証リンクを確認
4. 新しいアカウントでログイン

## 設定

`src/main.tsx` を編集してKeycloak設定を変更：

```typescript
const AUTH_CONFIG = {
  authority: 'http://localhost:8080/realms/common-auth',
  clientId: 'example-app',
  redirectUri: 'http://localhost:3000/callback',
  postLogoutRedirectUri: 'http://localhost:3000',
}
```

## トラブルシューティング

### "Invalid redirect_uri" エラー

Keycloakクライアント設定でリダイレクトURIが一致していることを確認：
- `http://localhost:3000/*` （ワイルドカード付き）

### CORSエラー

KeycloakクライアントのWeb Origins設定を確認：
- `http://localhost:3000`

### 400エラー（クライアントが見つからない）

Auth Stackを再起動してRealmを再インポートしてください：
```bash
cd ../../auth-stack
docker-compose down -v
docker-compose up -d
```

数分待ってから、http://localhost:8080 で `example-app` クライアントが存在することを確認してください。

### パスワードリセットメールが届かない

`auth-stack/.env` でSMTPを設定：
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

その後Auth Stackを再起動：
```bash
docker-compose down && docker-compose up -d
```
