# 実装計画 #001 — Keycloak MFA

## 実装ステップ

### Step 1: メールOTP環境（顧客A）

**成果物**
- `infra/docker-compose.yml`
- `infra/keycloak/realm-export.json`
- `infra/keycloak/.env.example`

**検証手順（Red → Green）**
1. `docker compose up` で起動
2. `http://localhost:8080` でKeycloak管理UIにアクセス
3. テストユーザーでログイン → MailHog(`http://localhost:8025`)にOTPメールが届くことを確認
4. OTPコード入力 → ログイン完了を確認
5. 誤コード3回入力 → アカウントロックを確認

**追加検証（MUST）: Email OTP Provider ID確認**
1. `docker compose --env-file .env up -d` で起動
2. Keycloakログに `Failed to import realm` が出ていないことを確認
3. 管理UIで `Authentication > Flows > custom-mail-mfa-forms` を開く
4. `auth-email-otp-form` 実行が存在し `REQUIRED` であることを確認

### Step 2: TOTPフロー環境（顧客B）

**成果物**
- `infra/keycloak/realm-export-totp.json`
- `infra/docker-compose-totp.yml`

**検証手順（Red → Green）**

```bash
# Step 1 環境が起動中の場合は停止
docker compose --env-file .env down

# Step 2 環境を起動
docker compose -f docker-compose-totp.yml --env-file .env up -d
```

> ⚠️ **セッションキャッシュ対策:** 以下の検証は必ず **ブラウザのプライベートウィンドウ（シークレットモード）** で実施すること。通常ウィンドウでは既存セッションが残り、2回目ログインの挙動が正しく確認できない。

1. プライベートウィンドウで `http://localhost:8080/realms/mfa-realm-totp/account` にアクセス
2. `testuser-totp` / `Test1234!` でログイン
3. **初回:** パスワード変更画面 → QRコード設定画面の順に遷移することを確認
4. Google Authenticator / Authy 等でQRをスキャン → 6桁コードを入力 → ログイン完了を確認
5. ログアウト後、**新しいプライベートウィンドウ** で再ログイン
6. **2回目:** QRコード画面は表示されず、コード入力画面のみ表示を確認
7. **ブルートフォース検証:** 誤コードを3回入力 → アカウントロックを確認
   - Admin UI → Users → testuser-totp → 「Temporary locked」表示を確認
   - Admin UI からロック解除後、正しいコードでログイン成功を確認
8. **OTPリセット検証（Realm Admin限定）:**
   - Admin UI → Users → testuser-totp → Credentials タブ
   - 「OTP」の Delete ボタンを押す
   - 新しいプライベートウィンドウで再ログイン → QRコード設定画面が再表示されることを確認

**TOTP仕様確認**

| 項目 | 期待値 |
|------|--------|
| アルゴリズム | HMAC-SHA1 |
| 桁数 | 6桁 |
| 更新周期 | 30秒 |
| 互換アプリ | Google Authenticator / Authy / Microsoft Authenticator |

### Step 3: 本番用構成

**成果物**
- `infra/docker-compose.prod.yml`

**検証手順**
1. `.env` に実際のSMTP設定を記入
2. `docker compose -f docker-compose.prod.yml up` で起動
3. 実際のメールアドレスにOTPが届くことを確認

## 実装順序

```
Step 1 → Step 2 → Step 3
  └─ 各Step完了後に検証してから次へ進む
```

## 依存関係

- Keycloak v24以降
- Docker / Docker Compose v2以降
- PostgreSQL v16
