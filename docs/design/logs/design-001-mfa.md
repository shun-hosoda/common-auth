# 設計記録 #001 — Keycloak MFA 認証フロー設計

## 決定事項

### 1. 認証フロー構成

| フロー名 | 対象顧客 | ステップ |
|---------|---------|---------|
| `custom-mail-mfa-flow` | 顧客A（メールOTP） | Username/Password → Email OTP |
| `custom-totp-flow` | 顧客B（TOTPアプリ） | Username/Password → OTP（初回: Configure OTP） |

顧客切り替えは Realm の **Browser Flow Binding** を変更するだけで完結する。

> **[FIX: アーキテクト指摘] realm-export ファイル分離方針**
> `realm-export.json`（メールOTP）と `realm-export-totp.json`（TOTP）を別ファイルとして管理する。
> 共通設定（SMTP・DB接続・セキュリティポリシー）の二重管理リスクは、`.env` による環境変数注入で吸収する。
> 将来的に統合が必要になった場合は ADR-001 を改訂すること。

### 2. セキュリティパラメータ

| 項目 | 値 |
|------|-----|
| OTP桁数 | 6桁 |
| OTP有効期限 | 5分 |
| 試行上限 | 3回（超過でロック） |
| TOTPアルゴリズム | HMAC-SHA1 / 30秒 |
| 信頼済みCookie有効期限 | 30日（環境変数で変更可） |
| Cookie属性 | SameSite=Strict, Secure, HttpOnly |

### 3. インフラ構成

```
docker-compose.yml
  ├─ keycloak (v24+)
  │    └─ 起動時に realm-export.json を自動インポート
  ├─ postgres (v16)
  │    └─ Keycloak内部DB
  │    └─ healthcheck 設定必須（keycloak は depends_on: condition: service_healthy を使用）
  └─ mailhog (開発用SMTPモック)
       └─ ポート: 1025（SMTP）/ 8025（WebUI）
       └─ サービス名: mailhog
```

> **[FIX: DBスペシャリスト指摘]** Keycloakは `depends_on: condition: service_healthy` を使用し、PostgreSQLのhealthcheck完了後に起動すること。healthcheckコマンドは `pg_isready -U keycloak` を使用する。

本番環境では `mailhog` を削除し、環境変数でSMTP接続情報を注入する。

### 4. 環境変数定義

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| `KC_SMTP_HOST` | SMTPホスト | `mailhog` |
| `KC_SMTP_PORT` | SMTPポート | `1025` |
| `KC_SMTP_FROM` | 送信元アドレス | `noreply@example.com` |
| `KC_SMTP_AUTH` | SMTP認証有無 | `false` |
| `KC_SMTP_USER` | SMTPユーザー | — |
| `KC_SMTP_PASSWORD` | SMTPパスワード | ⚠️ プレースホルダーのみ記載（実値は `.env` に設定） |
| `KC_SMTP_SSL` | SSL有効 | `false` |
| `KC_SMTP_TLS` | TLS有効 | `false` |
| `KC_OTP_EXPIRES_IN` | OTP有効期限（秒） | `300` |
| `KC_COOKIE_MAX_AGE` | 信頼済みCookie期間（秒） | `2592000` |
| `KC_DB_URL` | PostgreSQL接続URL | — |
| `KC_DB_USERNAME` | DBユーザー | `keycloak` |
| `KC_DB_PASSWORD` | DBパスワード | ⚠️ プレースホルダーのみ記載（実値は `.env` に設定） |

> **[FIX: セキュリティ指摘 MUST]** シークレット管理ルール
> - `.env.example` にはプレースホルダー（例: `your-db-password-here`）のみを記載する
> - 実際のシークレット値を含む `.env` は **必ず `.gitignore` に追加する**
> - リポジトリに実際のパスワード・APIキーを含むファイルをコミットしてはならない

### 5. メールOTP再送設計

> **[FIX: PM指摘]** NFR-02（メール未着時のリトライ手段）の実現方法

Keycloak v24 の Email OTP 画面には標準で「再送」リンクが含まれる。
カスタムテーマを使用する場合は `email-otp-form.ftl` に再送ボタンを明示的に配置すること。

### 6. ファイル構成（成果物）

```
infra/
  ├─ docker-compose.yml
  ├─ docker-compose.prod.yml      # 本番用（mailhog除去）
  └─ keycloak/
       ├─ realm-export.json       # 顧客A: メールOTPフロー定義
       ├─ realm-export-totp.json  # 顧客B: TOTPフロー定義
       └─ .env.example            # 環境変数テンプレート（シークレット値なし）
.gitignore                        # .env を必ず含めること
```

### 7. OTPリセット運用フロー

> **[FIX: セキュリティ指摘]** 管理者の認可要件を追記

**実行権限: Realm Admin ロールを持つユーザーのみ**

```
Realm Admin → Keycloak Admin UI
  → Users → 対象ユーザー → Credentials タブ
  → 「OTP」の Delete ボタン
  → 次回ログイン時に初期設定フロー再実行
```

Admin REST API でも同様に実施可能（Realm Admin トークン必須）：
`DELETE /admin/realms/{realm}/users/{userId}/credentials/{credentialId}`

一般ユーザー・アプリサービスアカウントからこのエンドポイントへのアクセスは **403 Forbidden** となる（Keycloak デフォルト動作）。

### 8. Phase 2: 信頼済みデバイス（Cookie）設計方針

> **[FIX: シニアエンジニア指摘]** Phase 1との非干渉性を確認

- Phase 1（メールOTP）の認証フローとは **独立したステップ**として実装する
- Keycloak の Cookie Authenticator を `custom-mail-mfa-flow` に追加し、`ALTERNATIVE` として配置
- Cookie が存在する場合: Email OTP ステップをスキップ
- Cookie が存在しない場合: Email OTP → 認証成功後にCookieを発行
- Phase 1では Cookie ステップを **無効化した状態**で納品し、Phase 2で有効化する
- Phase 1設定とPhase 2設定は同一の `realm-export.json` 内でフラグ制御可能（`KC_MFA_COOKIE_ENABLED=false`）
