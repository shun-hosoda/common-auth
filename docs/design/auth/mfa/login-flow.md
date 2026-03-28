# MFAログインフロー — 初回設定・認証

**更新日**: 2026-03-24
**対象PRD**: Phase 3.5 (FR-036)

> **⚠️ KC 24.0.5 制約**: Email OTP (`auth-email-otp-form`) は Keycloak 26+ で追加された機能のため、
> 現行環境（KC 24.0.5）では **TOTP のみ対応**。Email OTP は KC 26+ アップグレード時に対応予定。

---

## 概要

MFAが有効なテナントのユーザーがログインする際の認証フロー。
初回（MFA未設定）は設定フロー、2回目以降は検証フローに分岐する。

---

## 1. Keycloak統合認証フロー

### フロー構造（現行: TOTP のみ）

```
unified-mfa-browser (top-level)
├── Cookie (ALTERNATIVE)  ← 既存セッションならスキップ
└── Forms (ALTERNATIVE)
    ├── Username/Password (REQUIRED)
    └── MFA Gate (CONDITIONAL)
        ├── Condition: user.mfa_enabled = "true" (REQUIRED)
        │
        └── TOTP Subflow (CONDITIONAL)
            ├── Condition: user.mfa_method = "totp" (REQUIRED)
            └── OTP Form (REQUIRED)
                 ├── OTP未設定 → CONFIGURE_TOTP Required Action → QR表示
                 └── OTP設定済み → 6桁コード入力
```

> **将来拡張（KC 26+）**: TOTP Subflow と並列に Email OTP Subflow を追加可能な構造。
> `mfa-gate` 内に `priority: 30` で `email-subflow` を追加するだけで対応できる。

### authenticatorConfig（現行: 2件）

| alias | attribute_name | expected_value | not_set_condition |
|-------|---------------|----------------|-------------------|
| `mfa-gate-condition` | `mfa_enabled` | `true` | `skip` |
| `mfa-totp-condition` | `mfa_method` | `totp` | `skip` |

> **KC 26+ 追加予定**: `mfa-email-condition` (`mfa_method` = `email`) + `email-otp-config` (`length=6, ttl=300, attempts=3`)

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
    ├─ mfa_enabled = "true" かつ mfa_method = "totp"
    │   │
    │   ├─ OTP未設定（初回）──────────► ★ TOTP初回設定フロー（後述）
    │   │
    │   └─ OTP設定済み ──────────────► TOTP入力画面 → コード検証 → ログイン完了
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

## 4. Email OTPフロー（KC 26+ 対応予定）

> **⚠️ 未実装**: `auth-email-otp-form` は Keycloak 26 以降で追加された Authenticator Provider であり、
> 現行環境（KC 24.0.5）では利用不可。KC 26+ へのアップグレード後に対応予定。

### KC 26+ 対応時の変更点

1. `realm-export.json` に `unified-mfa-browser email-subflow` フローを追加
2. `authenticatorConfig` に `mfa-email-condition` + `email-otp-config` を追加
3. Backend API の `MfaSettingsBody.mfa_method` に `"email"` を許可
4. Frontend のメールOTP ラジオボタンを有効化

### 参考: Email OTPの特徴

- **初回設定が不要**: TOTP と異なりQRスキャン等のセットアップがない
- **クレデンシャル不要**: ログイン時にその場でメール送信するため、事前のクレデンシャル登録がない
- **Required Action不要**: `CONFIGURE_TOTP` は付与しない（Email OTPはその場で完結）
- **セキュリティ強度**: 中（メール盗聴リスクあり）— TOTP（高）より劣る

---

## 5. MFA方式別の比較

| 項目 | TOTP | Email OTP（KC 26+ 予定） |
|------|------|-------------------|
| 初回設定 | 必要（QRスキャン） | 不要 |
| Required Action | `CONFIGURE_TOTP` | なし |
| クレデンシャル保存 | あり（Keycloak） | なし |
| オフライン利用 | ✅ 可能 | ❌ メール必須 |
| ユーザー体験 | やや複雑（初回のみ） | シンプル |
| セキュリティ強度 | 高（デバイス所持） | 中（メール盗聴リスク） |
| 方式変更時のリセット | OTPクレデンシャル削除 | なし |
| **対応状況** | **✅ 実装済** | **⚠️ KC 26+ 待ち** |

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
    │   └─ mfa_method = totp → CONFIGURE_TOTP Required Action 追加
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
| TOTP設定画面でブラウザを閉じた | 次回ログイン時に再度TOTP設定画面が表示（Required Action残存） |
| super_admin が複数テナントに属する | super_admin の MFA 属性は **プライマリテナント（`tenant_id` ユーザー属性のテナント）のポリシーに従う**。他テナントの MFA ポリシー変更時、super_admin の属性は更新しない（`tenant_id` が対象テナントと一致する場合のみ更新） |

---

## 8. realm-export.json 変更

`auth-stack/keycloak/realm-export.json` に追加:

- `authenticationFlows`: 統合MFAフロー定義（4フロー）
- `authenticatorConfig`: 条件設定（2エントリ）
- `browserFlow`: `"unified-mfa-browser"`
- `requiredActions`: `CONFIGURE_TOTP`（既存、変更なし）

> **KC 26+ 対応時**: email-subflow (1フロー) + authenticatorConfig (2エントリ) を追加予定

→ 具体的なJSON定義は [tenant-policy.md](tenant-policy.md) の realm-export セクションを参照

### authenticationFlows JSON定義（現行版: TOTPのみ）

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
    }
  ],
  "authenticatorConfig": [
    {
      "alias": "mfa-gate-condition",
      "config": {
        "attribute_name": "mfa_enabled",
        "attribute_expected_value": "true",
        "not": "false"
      }
    },
    {
      "alias": "mfa-totp-condition",
      "config": {
        "attribute_name": "mfa_method",
        "attribute_expected_value": "totp",
        "not": "false"
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

> **KC 26+ 対応時追加予定**: `email-otp-form.ftl`（Email OTPコード入力 + 再送ボタン）

初期実装ではKeycloakデフォルトテーマを使用し、カスタムテーマは後追い対応。
