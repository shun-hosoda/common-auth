# MFA インフラストラクチャ設計書 — Keycloak 認証フロー基盤

## 1. 概要

Keycloak v24+ を使用したMFA認証フローの基盤設計。
メールOTPとTOTPの両方式をサポートし、テナント単位で切り替え可能とする。

> テナント単位のMFAポリシー管理は [テナントMFAポリシー設計](tenant-policy.md) を参照。
> 認証フロー（統合MFAブラウザフロー）の詳細は [ログインフロー設計](login-flow.md) を参照。

---

## 2. 認証フロー構成

| フロー名 | 対象 | ステップ |
|---------|------|---------|
| `custom-mail-mfa-flow` | メールOTPテナント | Username/Password → Email OTP |
| `custom-totp-flow` | TOTPテナント | Username/Password → OTP（初回: Configure OTP） |
| `unified-mfa-browser` | 統合フロー（Phase 3.5） | Username/Password → Conditional MFA Gate |

> Phase 3.5で `unified-mfa-browser` を導入し、テナントグループ属性に基づく動的MFA方式切替を実現。
> 詳細は [ログインフロー設計](login-flow.md) を参照。

---

## 3. セキュリティパラメータ

| 項目 | 値 |
|------|-----|
| OTP桁数 | 6桁 |
| OTP有効期限 | 5分（300秒） |
| 試行上限 | 3回（超過でロック） |
| TOTPアルゴリズム | HMAC-SHA1 / 30秒 |
| 信頼済みCookie有効期限 | 30日（環境変数で変更可） |
| Cookie属性 | SameSite=Strict, Secure, HttpOnly |

---

## 4. インフラ構成

```
docker-compose.yml
  ├─ keycloak (v24+)
  │    └─ 起動時に realm-export.json を自動インポート
  ├─ postgres (v16)
  │    └─ healthcheck: pg_isready -U keycloak
  │    └─ keycloakは depends_on: condition: service_healthy
  └─ mailhog (開発用SMTPモック)
       └─ SMTP: 1025 / WebUI: 8025
```

本番環境では `mailhog` を削除し、環境変数でSMTP接続情報を注入する。

---

## 5. 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| `KC_SMTP_HOST` | SMTPホスト | `mailhog` |
| `KC_SMTP_PORT` | SMTPポート | `1025` |
| `KC_SMTP_FROM` | 送信元アドレス | `noreply@example.com` |
| `KC_SMTP_AUTH` | SMTP認証有無 | `false` |
| `KC_SMTP_USER` | SMTPユーザー | — |
| `KC_SMTP_PASSWORD` | SMTPパスワード | `.env` で管理 |
| `KC_SMTP_SSL` | SSL有効 | `false` |
| `KC_SMTP_TLS` | TLS有効 | `false` |
| `KC_OTP_EXPIRES_IN` | OTP有効期限（秒） | `300` |
| `KC_COOKIE_MAX_AGE` | 信頼済みCookie期間（秒） | `2592000` |
| `KC_DB_URL` | PostgreSQL接続URL | — |
| `KC_DB_USERNAME` | DBユーザー | `keycloak` |
| `KC_DB_PASSWORD` | DBパスワード | `.env` で管理 |

### シークレット管理ルール

- `.env.example` にはプレースホルダーのみ記載（例: `your-db-password-here`）
- 実際のシークレット値を含む `.env` は `.gitignore` に追加
- リポジトリに実際のパスワード・APIキーをコミットしてはならない

---

## 6. メールOTP再送

Keycloak v24の Email OTP画面には標準で「再送」リンクが含まれる。
カスタムテーマ使用時は `email-otp-form.ftl` に再送ボタンを明示的に配置すること。

---

## 7. OTPリセット運用フロー

**実行権限: Realm Admin ロールを持つユーザーのみ**

```
Realm Admin → Keycloak Admin UI
  → Users → 対象ユーザー → Credentials タブ
  → 「OTP」の Delete ボタン
  → 次回ログイン時に初期設定フロー再実行
```

Admin REST API でも同様:
```
DELETE /admin/realms/{realm}/users/{userId}/credentials/{credentialId}
```

一般ユーザー・サービスアカウントからは 403 Forbidden（Keycloakデフォルト動作）。

---

## 8. 信頼済みデバイス（Cookie）設計

- Keycloak の Cookie Authenticator を認証フローに `ALTERNATIVE` として配置
- Cookie存在時: MFAステップをスキップ
- Cookie不存在時: MFA認証 → 成功後にCookieを発行
- Phase 1では Cookie ステップを無効化した状態で提供
- Phase 2で有効化（`KC_MFA_COOKIE_ENABLED`で制御）

---

## 9. ファイル構成

```
auth-stack/
├── docker-compose.yml
├── .env.example
└── keycloak/
    ├── realm-export.json           # メインRealm設定
    └── realm-export-totp.json      # TOTP専用フロー（顧客B用）
infra/
├── docker-compose.yml              # 開発環境
├── docker-compose-totp.yml         # TOTP開発環境
└── keycloak/
    ├── realm-export.json
    └── realm-export-totp.json
```

> `realm-export.json` と `realm-export-totp.json` を別ファイル管理。
> 共通設定（SMTP・DB接続・セキュリティポリシー）は `.env` で吸収。
> 将来的に統合が必要な場合は ADR-001 改訂で対応。

---

*元ログ: [設計記録 #001 — Keycloak MFA 認証フロー設計](../logs/design-001-mfa.md)*
