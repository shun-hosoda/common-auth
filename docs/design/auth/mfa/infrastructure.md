# MFA インフラストラクチャ設計書 — Keycloak 認証フロー基盤

## 1. 概要

Keycloak v24+ を使用したMFA認証フローの基盤設計。
メールOTPとTOTPの両方式をサポートし、テナント単位で切り替え可能とする。

> テナント単位のMFAポリシー管理は [テナントMFAポリシー設計](tenant-policy.md) を参照。
> 認証フロー（統合MFAブラウザフロー）の詳細は [ログインフロー設計](login-flow.md) を参照。

---

## 2. 認証フロー構成

現在は `unified-mfa-browser` フロー1本に統合済み。

| フロー / サブフロー | 用途 |
|-------------------|------|
| `unified-mfa-browser` | メインブラウザフロー（`browserFlow` に設定） |
| `unified-mfa-browser forms` | フォーム認証サブフロー |
| `unified-mfa-browser mfa-gate` | MFA条件分岐サブフロー（`conditional-user-attribute` で判定） |

> テナントグループ属性 (`mfa_enabled`, `mfa_method`) に基づく動的MFA方式切替を実現。
> 詳細は [ログインフロー設計](login-flow.md) を参照。
>
> **廃止済み**: `custom-mail-mfa-flow`, `custom-totp-flow` は `unified-mfa-browser` に統合されたため削除。

---

## 3. セキュリティパラメータ

| 項目 | 値 |
|------|-----|
| OTP桁数 | 6桁 |
| OTP有効期限 | 5分（300秒） |
| 試行上限 | 3回（超過でロック） |
| TOTPアルゴリズム | HmacSHA256 / 30秒 |
| 信頼済みCookie有効期限 | 30日（環境変数で変更可） |
| Cookie属性 | SameSite=Strict, Secure, HttpOnly |

---

## 4. インフラ構成

```
auth-stack/docker-compose.yml
  ├─ keycloak (v24+)
  │    └─ 起動時に realm-export.json を自動インポート
  ├─ keycloak-db (postgres:16)
  │    └─ healthcheck: pg_isready -U keycloak
  │    └─ keycloakは depends_on: condition: service_healthy
  ├─ app-db (postgres:16)
  │    └─ 業務DB（user_profiles, tenant_groups 等）
  │    └─ port: 5433
  └─ mailhog (開発用SMTPモック)
       └─ SMTP: 1025 / WebUI: 8025
```

本番環境では `mailhog` を削除し、環境変数でSMTP接続情報を注入する。

---

## 5. 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| `SMTP_HOST` | SMTPホスト | `mailhog` |
| `SMTP_PORT` | SMTPポート | `1025` |
| `SMTP_FROM` | 送信元アドレス | `noreply@example.com` |
| `SMTP_FROM_DISPLAY_NAME` | 送信元表示名 | `Common Auth` |
| `SMTP_AUTH` | SMTP認証有無 | `false` |
| `SMTP_USER` | SMTPユーザー | — |
| `SMTP_PASSWORD` | SMTPパスワード | `.env` で管理 |
| `SMTP_SSL` | SSL有効 | `false` |
| `SMTP_STARTTLS` | STARTTLS有効 | `false` |
| `KC_DB_URL` | Keycloak DB接続URL | — |
| `KC_DB_USERNAME` | Keycloak DBユーザー | `keycloak` |
| `KC_DB_PASSWORD` | Keycloak DBパスワード | `.env` で管理 |

> docker-compose.yml では `KC_SPI_EMAIL_TEMPLATE_SMTP_SERVER_*` 形式で
> 上記 `SMTP_*` 変数を参照する（例: `${SMTP_HOST:-mailhog}`）。

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
auth-stack/                          # ← メインの認証スタック
├── docker-compose.yml               #   4サービス (keycloak, keycloak-db, app-db, mailhog)
├── .env.example
├── keycloak/
│   └── realm-export.json            #   統合Realm設定（unified-mfa-browser フロー含む）
└── postgres/
    └── init.sql                     #   業務DB初期化スクリプト
infra/                               # ← レガシー（開発検証用、参考として残存）
├── docker-compose.yml
├── docker-compose-totp.yml
└── keycloak/
    ├── realm-export.json
    └── realm-export-totp.json
```

> `unified-mfa-browser` への統合完了により、`realm-export-totp.json` は不要。
> `infra/` 配下は過去の検証構成として残存しているが、本番利用は `auth-stack/` を使用すること。

---

*元ログ: [設計記録 #001 — Keycloak MFA 認証フロー設計](../logs/design-001-mfa.md)*
