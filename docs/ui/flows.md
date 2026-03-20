# 画面遷移フロー

## 全体フロー

```
[ブラウザアクセス]
      │
      ▼
   / (Home)
      │
      ├─ 認証済み ──────────────────► /dashboard
      │
      └─ 未認証 ───► Keycloak ログイン画面
                           │
                           ├─ ログイン成功（MFA無効）──► /callback ──► /dashboard
                           │
                           ├─ ログイン成功（MFA有効）
                           │     │
                           │     ├─ TOTP未設定 ──► TOTP初回設定 ──► /callback ──► /dashboard
                           │     ├─ TOTP設定済み ──► TOTP入力 ──► /callback ──► /dashboard
                           │     └─ Email OTP ──► メールコード入力 ──► /callback ──► /dashboard
                           │
                           ├─ パスワードリセット ──► (Keycloak) ──► /dashboard
                           │
                           └─ ログイン失敗 ──► Keycloak エラー表示
```

## ダッシュボード内遷移

```
/dashboard
    │
    ├─ [MFAステータスカード]（MFA有効テナントのみ表示）
    │       ├─ 「設定を変更する →」 ──► Keycloak Account Console /account/totp
    │       └─ 「今すぐ設定する →」 ──► Keycloak Account Console /account/totp
    │
    ├─ [サイドナビ] ユーザー管理 (tenant_admin / super_admin のみ)
    │       └──► /admin/users
    │                 ├─ ユーザー一覧
    │                 ├─ [ユーザー登録ボタン] ──► 登録モーダル
    │                 └─ [行クリック] ──► 編集モーダル
    │
    ├─ [サイドナビ] セキュリティ設定 (tenant_admin / super_admin のみ)
    │       └──► /security
    │                 ├─ MFA有効/無効トグル
    │                 ├─ MFA方式選択（TOTP / Email OTP）
    │                 └─ [保存する] ──► 全ユーザーに適用
    │
    └─ [UserDropdown]
            ├─ アカウント設定 ──► Keycloak Account Console /account/
            └─ ログアウト ──────► Keycloak ログアウト ──► / (Home)
```

## 画面一覧

| パス | 画面名 | アクセス条件 | 設計書 |
|---|---|---|---|
| `/` | Home（リダイレクター） | 全員 | — |
| `/callback` | OAuthコールバック | 全員 | — |
| `/dashboard` | ダッシュボード | 認証済み | [dashboard.md](screens/dashboard.md) |
| `/admin/users` | ユーザー管理 | `tenant_admin` / `super_admin` | [admin-users.md](screens/admin-users.md) |
| `/security` | セキュリティ設定 | `tenant_admin` / `super_admin` | [../design/auth/mfa/tenant-policy.md](../design/auth/mfa/tenant-policy.md) |
| (Keycloak) | TOTP初回設定 | MFA有効テナントのユーザー | [../design/auth/mfa/login-flow.md](../design/auth/mfa/login-flow.md) |
| (Keycloak) | MFAコード入力 | MFA有効テナントのユーザー | [../design/auth/mfa/login-flow.md](../design/auth/mfa/login-flow.md) |
| (Keycloak) | Account Console | 認証済み | [../design/auth/mfa/account-settings.md](../design/auth/mfa/account-settings.md) |

## 認可マトリックス

| 画面 / 操作 | user | tenant_admin | super_admin |
|---|:---:|:---:|:---:|
| ダッシュボード表示 | ✅ | ✅ | ✅ |
| MFAステータスカード表示 | ✅ | ✅ | ✅ |
| アカウント設定（自分のMFA管理） | ✅ | ✅ | ✅ |
| ユーザー管理メニュー表示 | — | ✅ | ✅ |
| セキュリティ設定メニュー表示 | — | ✅ | ✅ |
| 自テナントMFAポリシー変更 | — | ✅ | ✅ |
| 自テナントユーザー管理 | — | ✅ | ✅ |
| 全テナントユーザー管理 | — | — | ✅ |
| Keycloak管理コンソール | — | — | ✅ |
