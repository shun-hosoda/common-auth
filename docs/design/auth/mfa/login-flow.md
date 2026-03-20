# MFAログインフロー — 初回設定・認証

**更新日**: 2026-03-20
**対象PRD**: Phase 3.5 (FR-036)

---

## 概要

MFAが有効なテナントのユーザーがログインする際の認証フロー。
初回（MFA未設定）は設定フロー、2回目以降は検証フローに分岐する。

---

## 1. Keycloak統合認証フロー

### フロー構造

```
unified-mfa-browser (top-level)
├── Cookie (ALTERNATIVE)  ← 既存セッションならスキップ
└── Forms (ALTERNATIVE)
    ├── Username/Password (REQUIRED)
    └── MFA Gate (CONDITIONAL)
        ├── Condition: user.mfa_enabled = "true" (REQUIRED)
        │
        ├── TOTP Subflow (CONDITIONAL)
        │   ├── Condition: user.mfa_method = "totp" (REQUIRED)
        │   └── OTP Form (REQUIRED)
        │        ├── OTP未設定 → CONFIGURE_TOTP Required Action → QR表示
        │        └── OTP設定済み → 6桁コード入力
        │
        └── Email OTP Subflow (CONDITIONAL)
            ├── Condition: user.mfa_method = "email" (REQUIRED)
            └── Email OTP Form (REQUIRED)
                 └── メールでワンタイムコード送信 → 6桁コード入力
```

### authenticatorConfig

| alias | attribute_name | expected_value | not_set_condition |
|-------|---------------|----------------|-------------------|
| `mfa-gate-condition` | `mfa_enabled` | `true` | `skip` |
| `mfa-totp-condition` | `mfa_method` | `totp` | `skip` |
| `mfa-email-condition` | `mfa_method` | `email` | `skip` |
| `email-otp-config` | — | — | `length=6, expiration=300s, attempts=3` |

---

## 2. ログインフロー全体図

```
[ユーザー] ブラウザアクセス
    │
    ▼
[アプリ]  認証チェック → 未認証 → Keycloakリダイレクト
    │
    ▼
[Keycloak] ログイン画面
    │
    ├─ ID/PW入力
    │
    ▼
[Keycloak] MFA Gate 判定
    │
    ├─ mfa_enabled ≠ "true"  ────────────► ログイン完了 → /callback → /dashboard
    │
    ├─ mfa_enabled = "true"
    │   │
    │   ├─ mfa_method = "totp"
    │   │   │
    │   │   ├─ OTP未設定（初回）──────────► ★ TOTP初回設定フロー（後述）
    │   │   │
    │   │   └─ OTP設定済み ──────────────► TOTP入力画面 → コード検証 → ログイン完了
    │   │
    │   └─ mfa_method = "email"
    │       │
    │       └─ メールOTP送信 ────────────► Email OTP入力画面 → コード検証 → ログイン完了
    │
    ▼
[アプリ]  /callback → /dashboard
```

---

## 3. TOTP初回設定フロー（MFA未設定ユーザー）

### トリガー条件

- テナントの `mfa_enabled = true` かつ `mfa_method = totp`
- ユーザーに `CONFIGURE_TOTP` Required Action が付与されている
- ユーザーにOTPクレデンシャルがまだ存在しない

### Keycloak標準動作

Keycloakは `CONFIGURE_TOTP` Required Action が付与されたユーザーのログイン時に、
自動的にTOTP設定画面を表示する。**カスタム実装不要。**

### 画面フロー

```
[Keycloak] ID/PW認証成功
    │
    ▼
[Keycloak] TOTP設定画面（Required Action: CONFIGURE_TOTP）
    │
    │  ┌──────────────────────────────────────────┐
    │  │  二段階認証の設定                          │
    │  │                                          │
    │  │  1. 認証アプリをインストール               │
    │  │     Google Authenticator                  │
    │  │     Microsoft Authenticator               │
    │  │     Authy                                 │
    │  │                                          │
    │  │  2. QRコードをスキャン                     │
    │  │     ┌──────────┐                          │
    │  │     │ [QRコード] │                         │
    │  │     └──────────┘                          │
    │  │     手動入力: XXXX-XXXX-XXXX-XXXX         │
    │  │                                          │
    │  │  3. 認証コードを入力                       │
    │  │     [______]                              │
    │  │                                          │
    │  │  [設定完了]                                │
    │  └──────────────────────────────────────────┘
    │
    ├─ 6桁コード入力 → 検証成功
    │
    ▼
[Keycloak] Required Action 完了 → CONFIGURE_TOTP 削除
    │
    ▼
ログイン完了 → /callback → /dashboard
```

### カスタムテーマ対応

`auth-stack/keycloak/themes/common-auth/login/` に以下テンプレートが必要：

| テンプレート | 用途 | 必要度 |
|---|---|---|
| `login-config-totp.ftl` | TOTP初回設定画面 | Should（デフォルトテーマでも動作） |
| `login-otp.ftl` | TOTP入力画面（2回目以降） | Should |

---

## 4. Email OTPフロー

### トリガー条件

- テナントの `mfa_enabled = true` かつ `mfa_method = email`
- Keycloak v24+ で `auth-email-otp-form` Authenticator が有効

### 画面フロー

```
[Keycloak] ID/PW認証成功
    │
    ▼
[Keycloak] メールOTP送信（自動）→ MailHog/SMTP
    │
    │  ┌──────────────────────────────────────────┐
    │  │  メール認証                                │
    │  │                                          │
    │  │  ご登録のメールアドレスに                    │
    │  │  認証コードを送信しました。                  │
    │  │                                          │
    │  │  user@example.com                        │
    │  │                                          │
    │  │  認証コード:                               │
    │  │  [______]                                │
    │  │                                          │
    │  │  [認証する]                               │
    │  │                                          │
    │  │  コードが届かない場合 [再送信]              │
    │  └──────────────────────────────────────────┘
    │
    ├─ 6桁コード入力 → 検証成功
    │
    ▼
ログイン完了 → /callback → /dashboard
```

### Email OTPパラメータ

| パラメータ | 値 | 説明 |
|---|---|---|
| コード桁数 | 6桁 | `emailOtpLength` |
| 有効期限 | 300秒（5分） | `emailOtpExpirationPeriod` |
| 送信試行上限 | 3回 | `emailOtpSendAttempts` |
| 再送ボタン | あり | Keycloak v24標準 |

### ブルートフォース保護

Email OTP のコード入力試行には Keycloak の **Realm ブルートフォース設定** が適用される。

| 設定 | 値（realm-export.json） | 効果 |
|------|------|------|
| `failureFactor` | 30 | 30回失敗でアカウントロック |
| `maxFailureWaitSeconds` | 900 | 最大ロック15分 |
| `quickLoginCheckMilliSeconds` | 1000 | 1秒以内の連続試行検出 |

Email OTP 固有の制限:
- `emailOtpSendAttempts=3`: 再送上限3回（コード入力失敗とは別カウント）
- `emailOtpExpirationPeriod=300s`: 5分経過でコード失効

### メールOTPの特徴

- **初回設定が不要**: TOTP と異なりQRスキャン等のセットアップがない
- **クレデンシャル不要**: ログイン時にその場でメール送信するため、事前のクレデンシャル登録がない
- **Required Action不要**: `CONFIGURE_TOTP` は付与しない（Email OTPはその場で完結）

---

## 5. MFA方式別の比較

| 項目 | TOTP | Email OTP |
|------|------|-----------|
| 初回設定 | 必要（QRスキャン） | 不要 |
| Required Action | `CONFIGURE_TOTP` | なし |
| クレデンシャル保存 | あり（Keycloak） | なし |
| オフライン利用 | ✅ 可能 | ❌ メール必須 |
| ユーザー体験 | やや複雑（初回のみ） | シンプル |
| セキュリティ強度 | 高（デバイス所持） | 中（メール盗聴リスク） |
| 方式変更時のリセット | OTPクレデンシャル削除 | なし |

---

## 6. 新規ユーザー追加時の挙動

テナント管理者がMFA有効テナントで新規ユーザーを作成した場合：

```
[Admin] POST /api/admin/users (新規ユーザー作成)
    │
    ▼
[Backend] テナントグループの mfa_enabled / mfa_method を取得
    │
    ├─ mfa_enabled = true:
    │   ├─ ユーザー属性に mfa_enabled, mfa_method を設定
    │   ├─ mfa_method = totp → CONFIGURE_TOTP Required Action 追加
    │   └─ mfa_method = email → Required Action 追加なし
    │
    └─ mfa_enabled = false:
        └─ MFA関連属性・Required Action は設定しない
```

> **実装ポイント**: `create_user` エンドポイントの既存処理に、テナントMFA設定の読み取りと属性付与を追加する。

---

## 7. エッジケース

| ケース | 挙動 |
|--------|------|
| MFA有効化直後、既にログイン済みのユーザー | 現セッションには影響なし。次回ログインからMFA要求 |
| MFA無効化後、OTPクレデンシャルが残っている | クレデンシャルは保持。再有効化時に再利用可能 |
| MFA方式変更（TOTP→Email） | 全ユーザーのOTPクレデンシャルをリセット。次回ログインでEmail OTP |
| Email OTP送信失敗（SMTP障害） | Keycloakがエラー表示。MailHog環境では発生しない |
| TOTP設定画面でブラウザを閉じた | 次回ログイン時に再度TOTP設定画面が表示（Required Action残存） |
| super_admin が複数テナントに属する | super_admin の MFA 属性は **プライマリテナント（`tenant_id` ユーザー属性のテナント）のポリシーに従う**。他テナントの MFA ポリシー変更時、super_admin の属性は更新しない（`tenant_id` が対象テナントと一致する場合のみ更新） |

---

## 8. realm-export.json 変更

`auth-stack/keycloak/realm-export.json` に追加:

- `authenticationFlows`: 統合MFAフロー定義（5フロー）
- `authenticatorConfig`: 条件設定（4エントリ）
- `browserFlow`: `"unified-mfa-browser"`
- `requiredActions`: `CONFIGURE_TOTP`（既存、変更なし）

→ 具体的なJSON定義は [tenant-policy.md](tenant-policy.md) の realm-export セクションを参照

### authenticationFlows JSON定義（完全版）

```json
{
  "authenticationFlows": [
    {
      "alias": "unified-mfa-browser",
      "description": "Browser flow with conditional MFA per tenant policy",
      "providerId": "basic-flow",
      "topLevel": true,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "auth-cookie",
          "requirement": "ALTERNATIVE",
          "priority": 10
        },
        {
          "flowAlias": "unified-mfa-browser forms",
          "requirement": "ALTERNATIVE",
          "priority": 20
        }
      ]
    },
    {
      "alias": "unified-mfa-browser forms",
      "description": "Username/password + conditional MFA",
      "providerId": "basic-flow",
      "topLevel": false,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "auth-username-password-form",
          "requirement": "REQUIRED",
          "priority": 10
        },
        {
          "flowAlias": "unified-mfa-browser mfa-gate",
          "requirement": "CONDITIONAL",
          "priority": 20
        }
      ]
    },
    {
      "alias": "unified-mfa-browser mfa-gate",
      "description": "MFA gate: check mfa_enabled attribute",
      "providerId": "basic-flow",
      "topLevel": false,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "conditional-user-attribute",
          "authenticatorConfig": "mfa-gate-condition",
          "requirement": "REQUIRED",
          "priority": 10
        },
        {
          "flowAlias": "unified-mfa-browser totp-subflow",
          "requirement": "CONDITIONAL",
          "priority": 20
        },
        {
          "flowAlias": "unified-mfa-browser email-subflow",
          "requirement": "CONDITIONAL",
          "priority": 30
        }
      ]
    },
    {
      "alias": "unified-mfa-browser totp-subflow",
      "description": "TOTP branch: check mfa_method=totp",
      "providerId": "basic-flow",
      "topLevel": false,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "conditional-user-attribute",
          "authenticatorConfig": "mfa-totp-condition",
          "requirement": "REQUIRED",
          "priority": 10
        },
        {
          "authenticator": "auth-otp-form",
          "requirement": "REQUIRED",
          "priority": 20
        }
      ]
    },
    {
      "alias": "unified-mfa-browser email-subflow",
      "description": "Email OTP branch: check mfa_method=email",
      "providerId": "basic-flow",
      "topLevel": false,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "conditional-user-attribute",
          "authenticatorConfig": "mfa-email-condition",
          "requirement": "REQUIRED",
          "priority": 10
        },
        {
          "authenticator": "auth-email-otp-form",
          "authenticatorConfig": "email-otp-config",
          "requirement": "REQUIRED",
          "priority": 20
        }
      ]
    }
  ],
  "authenticatorConfig": [
    {
      "alias": "mfa-gate-condition",
      "config": {
        "attribute_name": "mfa_enabled",
        "expected_attribute_value": "true",
        "not": "false"
      }
    },
    {
      "alias": "mfa-totp-condition",
      "config": {
        "attribute_name": "mfa_method",
        "expected_attribute_value": "totp",
        "not": "false"
      }
    },
    {
      "alias": "mfa-email-condition",
      "config": {
        "attribute_name": "mfa_method",
        "expected_attribute_value": "email",
        "not": "false"
      }
    },
    {
      "alias": "email-otp-config",
      "config": {
        "length": "6",
        "ttl": "300",
        "emailOtpSendAttempts": "3"
      }
    }
  ],
  "browserFlow": "unified-mfa-browser"
}
```

> **注意**: 上記JSONは realm-export.json の該当セクションにマージする。
> 既存の `requiredActions` (`CONFIGURE_TOTP`) は変更不要。

---

## 9. カスタムテーマ対応（Should）

| テンプレート | 画面 | 優先度 |
|---|---|---|
| `login-config-totp.ftl` | TOTP初回設定（QR表示） | Should |
| `login-otp.ftl` | TOTPコード入力 | Should |
| `email-otp-form.ftl` | Email OTPコード入力 + 再送ボタン | Should |

初期実装ではKeycloakデフォルトテーマを使用し、カスタムテーマは後追い対応。
