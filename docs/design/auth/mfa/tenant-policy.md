# テナントMFAポリシー管理 — 管理者設定

**更新日**: 2026-03-20
**対象PRD**: Phase 3.5 (FR-030〜FR-037)

---

## 概要

テナント管理者が自テナント全体のMFA有効/無効・方式を管理画面から設定する機能。

---

## 1. MFA設定ストレージ

**方式: グループ属性（真のソース）+ ユーザー属性ミラー**

```
グループ /tenants/acme-corp:
{
  "tenant_id": ["acme-corp"],
  "mfa_enabled": ["true"],       ← テナント設定
  "mfa_method": ["totp"]         ← "totp" | "email"
}

ユーザー attributes（認証フロー参照用ミラー）:
{
  "tenant_id": ["acme-corp"],
  "mfa_enabled": ["true"],       ← グループからミラー
  "mfa_method": ["totp"]         ← グループからミラー
}
```

- Keycloakの `conditional-user-attribute` はグループ属性を参照不可 → ユーザー属性にミラー
- **初期値**: `mfa_enabled: false`, `mfa_method: totp`

---

## 2. Backend API

### GET /api/admin/security/mfa

| 項目 | 値 |
|------|------|
| 権限 | `tenant_admin` / `super_admin` |
| レスポンス | `{ "mfa_enabled": bool, "mfa_method": "totp" \| "email" }` |
| データソース | テナントグループのグループ属性 |

### PUT /api/admin/security/mfa

| 項目 | 値 |
|------|------|
| 権限 | `tenant_admin` / `super_admin` |
| リクエスト | `{ "mfa_enabled": bool, "mfa_method": "totp" \| "email" }` |
| レスポンス | `{ "status": "updated", "mfa_enabled": bool, "mfa_method": str, "users_updated": int, "users_failed": int }` |

### 更新処理フロー

```
1. _require_admin(user) — 権限チェック
2. find_group_by_name(tenant_id) → get_group(group_id)
   — テナントグループ取得 + 現在のグループ属性（旧値）を保持
   旧値: old_mfa_enabled, old_mfa_method
3. グループ属性を更新 (mfa_enabled, mfa_method)
4. list_users(tenant_id) — テナント全ユーザー取得
5. 方式変更判定:
   old_mfa_method ≠ new_mfa_method かつ new_mfa_enabled = true
   → 全ユーザーのOTPクレデンシャルを一括リセット
6. ユーザー属性・Required Action を最終状態に基づき一括設定:
   a. new_mfa_enabled = true:
      - ユーザー属性: mfa_enabled="true", mfa_method=<グループ値で上書き>
      - new_mfa_method=totp → CONFIGURE_TOTP Required Action 追加
      - new_mfa_method=email → CONFIGURE_TOTP Required Action 削除
   b. new_mfa_enabled = false:
      - ユーザー属性: mfa_enabled="false"
      - mfa_method はグループ属性の値で上書き（再有効化時の不整合防止）
      - CONFIGURE_TOTP Required Action 削除
7. 一括更新は asyncio.Semaphore(10) で並列度制御
8. レスポンス返却（部分失敗時は失敗ユーザーIDリスト + 警告付き）
```

> **設計ポイント**:
> - Step 2 で `find_group_by_name` → `get_group(id)` の2段階取得が必要。
>   Keycloak Groups Search API はバージョンにより `attributes` を含まない場合がある。
>   `GET /groups/{id}` で確実にグループ属性を取得する。
> - Step 5 の方式変更判定を **ユーザー属性設定(Step 6)の前** に実行することで、
>   クレデンシャルリセット → 新方式設定 の順序を保証する。
> - Step 6 で `mfa_method` は有効/無効に関わらずグループ値で上書きし、
>   再有効化時のミラーリング不整合を防止する。

### KeycloakAdminClient 追加メソッド

```python
async def get_group(self, group_id: str) -> dict[str, Any]
async def update_group_attributes(self, group_id: str, attributes: dict[str, list[str]]) -> None
async def set_user_attributes_bulk(self, user_ids: list[str], attributes: dict[str, list[str]]) -> list[str]
async def add_required_action_bulk(self, user_ids: list[str], action: str) -> list[str]
async def remove_required_action_bulk(self, user_ids: list[str], action: str) -> list[str]
```

---

## 3. Frontend — セキュリティ設定画面

### ルーティング

```
/security — SecuritySettings.tsx（tenant_admin / super_admin のみ）
```

### SideNav構成

```
navItems:
├── ダッシュボード     (全ユーザー)
├── ユーザー管理       (tenant_admin / super_admin)
├── セキュリティ設定 ★ (tenant_admin / super_admin)
└── テナント管理       (super_admin のみ)
```

### 画面レイアウト

```
┌─────────────────────────────────────────────────┐
│ [Header + UserDropdown]                          │
├──────────┬──────────────────────────────────────┤
│ SideNav  │  セキュリティ設定                      │
│          │                                       │
│          │  ┌── MFA（多要素認証）──────────────┐  │
│          │  │                                  │  │
│          │  │  MFA を有効にする   [●トグル]     │  │
│          │  │                                  │  │
│          │  │  MFA方式:                        │  │
│          │  │  ◉ TOTP（認証アプリ）            │  │
│          │  │    Google Authenticator 等で      │  │
│          │  │    ワンタイムコードを生成          │  │
│          │  │  ○ メールOTP                     │  │
│          │  │    ログイン時にメールで            │  │
│          │  │    ワンタイムコードを送信          │  │
│          │  │                                  │  │
│          │  │  [保存する]                       │  │
│          │  └──────────────────────────────────┘  │
│          │                                       │
│          │  ⓘ 設定はテナント全体に適用されます。   │
│          │    次回ログイン時からMFAが要求されます。  │
└──────────┴──────────────────────────────────────┘
```

### 方式変更時の確認ダイアログ

```
⚠️ MFA方式の変更
MFA方式を「TOTP」→「メールOTP」に変更すると、
テナント内の全ユーザーのMFA設定がリセットされます。
各ユーザーは次回ログイン時に新しい方式でMFAを再設定する必要があります。

[キャンセル] [変更を適用]
```

---

## 4. テナント境界セキュリティ

| ロール | 読取 | 更新 | 対象 |
|--------|------|------|------|
| `tenant_admin` | ✅ | ✅ | 自テナントのみ |
| `super_admin` | ✅ | ✅ | 全テナント |
| `user` | ❌ | ❌ | 403 Forbidden |

---

## 5. パフォーマンス

- ユーザー一括更新: `asyncio.Semaphore(10)` で並列度制御
- 200ユーザー想定: 約200ms〜3秒
- 部分失敗時: 成功数・失敗数 + **失敗ユーザーIDリスト**をレスポンスに含め、ログに詳細記録
- リトライ: 管理者が「保存する」を再実行でリトライ可能（冪等性確保済み）

---

## 6. テスト計画

### テナントポリシーAPIテスト

| テストケース | 種別 | 対象 |
|---|---|---|
| GET /security/mfa — 初期状態 (mfa_enabled=false) | 正常 | admin router |
| GET /security/mfa — userロールで403 | 異常 | admin router |
| PUT /security/mfa — TOTP有効化 | 正常 | admin router |
| PUT /security/mfa — Email有効化 | 正常 | admin router |
| PUT /security/mfa — MFA無効化 | 正常 | admin router |
| PUT /security/mfa — 方式変更 (TOTP→Email) | 正常 | admin router |
| PUT /security/mfa — 方式変更 (Email→TOTP) | 正常 | admin router |
| PUT /security/mfa — userロールで403 | 異常 | admin router |
| PUT /security/mfa — 他テナントのグループにアクセス試行 | 異常 | admin router |
| PUT /security/mfa — 部分失敗 (モック) | 境界 | admin router |

### MFAステータスAPIテスト

| テストケース | 種別 | 対象 |
|---|---|---|
| GET /auth/mfa-status — MFA無効テナント | 正常 | auth router |
| GET /auth/mfa-status — MFA有効+TOTP設定済 | 正常 | auth router |
| GET /auth/mfa-status — MFA有効+TOTP未設定 | 正常 | auth router |
| GET /auth/mfa-status — MFA有効+Email OTP | 正常 | auth router |
| GET /auth/mfa-status — 未認証ユーザーで401 | 異常 | auth router |

---

## 7. 成果物一覧

| ファイル | 変更種別 |
|----------|---------|
| `auth-stack/keycloak/realm-export.json` | 変更: グループ属性追加 |
| `packages/backend-sdk/.../keycloak_admin_client.py` | 変更: グループ属性CRUD、一括更新メソッド |
| `packages/backend-sdk/.../routers/admin.py` | 変更: `/security/mfa` エンドポイント追加 |
| `examples/react-app/src/pages/SecuritySettings.tsx` | 新規: セキュリティ設定画面 |
| `examples/react-app/src/App.tsx` | 変更: ルート追加 |
| `examples/react-app/src/api/adminApi.ts` | 変更: MFA API関数追加 |
| `examples/react-app/src/pages/Dashboard.tsx` | 変更: navItems追加 |
| `examples/react-app/src/pages/AdminUsers.tsx` | 変更: navItems追加 |
| `packages/backend-sdk/tests/unit/test_admin_router.py` | 変更: テスト追加 |
