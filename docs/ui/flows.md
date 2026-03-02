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
                           ├─ ログイン成功 ──► /callback ──► /dashboard
                           │
                           ├─ パスワードリセット ──► (Keycloak) ──► /dashboard
                           │
                           └─ ログイン失敗 ──► Keycloak エラー表示
```

## ダッシュボード内遷移

```
/dashboard
    │
    ├─ [サイドナビ] ユーザー管理 (tenant_admin / super_admin のみ)
    │       └──► /admin/users
    │                 ├─ ユーザー一覧
    │                 ├─ [ユーザー登録ボタン] ──► 登録モーダル
    │                 └─ [行クリック] ──► 編集モーダル
    │
    └─ [UserDropdown]
            ├─ セキュリティ設定 ──► Keycloak Account (TOTP設定)
            └─ ログアウト ──────► Keycloak ログアウト ──► / (Home)
```

## 画面一覧

| パス | 画面名 | アクセス条件 | 設計書 |
|---|---|---|---|
| `/` | Home（リダイレクター） | 全員 | — |
| `/callback` | OAuthコールバック | 全員 | — |
| `/dashboard` | ダッシュボード | 認証済み | [dashboard.md](screens/dashboard.md) |
| `/admin/users` | ユーザー管理 | `tenant_admin` / `super_admin` | [admin-users.md](screens/admin-users.md) |

## 認可マトリックス

| 画面 / 操作 | user | tenant_admin | super_admin |
|---|:---:|:---:|:---:|
| ダッシュボード表示 | ✅ | ✅ | ✅ |
| ユーザー管理メニュー表示 | — | ✅ | ✅ |
| 自テナントユーザー管理 | — | ✅ | ✅ |
| 全テナントユーザー管理 | — | — | ✅ |
| Keycloak管理コンソール | — | — | ✅ |
