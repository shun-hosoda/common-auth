# 実装計画 — Phase 3.5 テナントMFAポリシー管理

**日時**: 2026-03-20
**対象設計書**:
- `docs/design/auth/mfa/tenant-policy.md`
- `docs/design/auth/mfa/login-flow.md`
- `docs/design/auth/mfa/account-settings.md`

---

## 実装Step分割

| Step | 内容 | 依存 |
|------|------|------|
| Step 1 | Backend基盤: `KeycloakAdminClient` 5メソッド拡張 | なし |
| Step 2 | Backend API: MFAポリシーAPI (admin) + MFAステータスAPI (auth) | Step 1 |
| Step 3 | Keycloak設定: realm-export.json 更新 | なし（並行可） |
| Step 4 | Frontend: SecuritySettings + MfaStatusCard + ルート・ナビ更新 | Step 2 |

---

## ファイル変更マップ

```
packages/backend-sdk/
├── src/common_auth/
│   ├── services/keycloak_admin_client.py  [変更] 5メソッド追加
│   └── routers/
│       ├── admin.py                       [変更] /security/mfa GET/PUT + create_user拡張
│       └── auth.py                        [変更] /mfa-status GET + _get_kc_admin
├── tests/unit/
│   ├── test_admin_router.py               [変更] MFAポリシーテスト10件追加
│   └── test_auth_router.py                [新規] MFAステータステスト5件

auth-stack/keycloak/
└── realm-export.json                      [変更] グループ属性 + 認証フロー + authenticatorConfig

examples/react-app/src/
├── App.tsx                                [変更] /security ルート追加
├── api/adminApi.ts                        [変更] MFA API 3関数追加
├── pages/
│   ├── Dashboard.tsx                      [変更] navItems + MfaStatusCard + dropdown
│   ├── AdminUsers.tsx                     [変更] navItems追加
│   └── SecuritySettings.tsx               [新規] セキュリティ設定画面
└── components/
    └── MfaStatusCard.tsx                  [新規] MFAステータスカード
```

---

## TDD実装順序

### Step 1: KeycloakAdminClient 拡張

| # | タスク | テスト |
|---|--------|--------|
| 1-1 | `get_group(group_id)` | mock: GET /groups/{id} → 属性付きグループ返却 |
| 1-2 | `update_group_attributes(group_id, attrs)` | mock: GET→PUT /groups/{id} 属性マージ確認 |
| 1-3 | `set_user_attributes_bulk(user_ids, attrs)` | mock: 3ユーザー一括更新、1件失敗→failed list |
| 1-4 | `add_required_action_bulk(user_ids, action)` | mock: 重複action追加なし確認 |
| 1-5 | `remove_required_action_bulk(user_ids, action)` | mock: action存在しない場合はスキップ確認 |

### Step 2: Backend API

| # | タスク | テスト |
|---|--------|--------|
| 2-1 | `GET /security/mfa` | 初期状態(false/totp), userロール403 |
| 2-2 | `PUT /security/mfa` — 有効化 | TOTP有効化, Email有効化 |
| 2-3 | `PUT /security/mfa` — 無効化 | MFA無効化（属性保持確認） |
| 2-4 | `PUT /security/mfa` — 方式変更 | TOTP→Email（リセット確認）, Email→TOTP |
| 2-5 | `PUT /security/mfa` — 権限チェック | userロール403, 他テナント403 |
| 2-6 | `PUT /security/mfa` — 部分失敗 | モックで1件失敗→users_failed=1 |
| 2-7 | `GET /mfa-status` — 各パターン | 無効テナント, TOTP設定済, TOTP未設定, Email OTP |
| 2-8 | `GET /mfa-status` — 認証チェック | 未認証401 |
| 2-9 | `create_user` 拡張 | MFA有効テナントでユーザー作成→属性+Required Action付与 |

### Step 3: Keycloak設定

| # | タスク | 検証方法 |
|---|--------|---------|
| 3-1 | グループ属性 `mfa_enabled`, `mfa_method` 初期値追加 | docker-compose down -v → up -d → グループ属性確認 |
| 3-2 | `authenticationFlows` 5件追加 | KeycloakログインでMFAフローが動作（mfa_enabled=true設定後） |
| 3-3 | `authenticatorConfig` 4件追加 | 同上 |
| 3-4 | `browserFlow` を `unified-mfa-browser` に変更 | 同上 |

### Step 4: Frontend

| # | タスク |
|---|--------|
| 4-1 | `adminApi.ts` — `getMfaSettings`, `updateMfaSettings`, `getMfaStatus` 追加 |
| 4-2 | `SecuritySettings.tsx` — トグル+ラジオ+保存+確認ダイアログ |
| 4-3 | `MfaStatusCard.tsx` — 3状態表示コンポーネント |
| 4-4 | `App.tsx` — `/security` ルート追加（AuthGuard + requiredRoles） |
| 4-5 | `Dashboard.tsx` — navItemsにセキュリティ設定追加 + MfaStatusCard表示 + dropdown変更 |
| 4-6 | `AdminUsers.tsx` — navItemsにセキュリティ設定追加 |

---

## アーキテクチャ決定

### _get_kc_admin 共通化方針

admin.pyの既存遅延初期化パターンを維持。auth.pyでは`app.state`からの読み取り専用アクセス。
`setup.py`は変更しない（`KC_ADMIN_CLIENT_SECRET`未設定時の起動エラー回避）。

```python
# auth.py に追加
def _get_kc_admin(request: Request) -> KeycloakAdminClient:
    if not hasattr(request.app.state, "kc_admin_client"):
        raise HTTPException(503, "Admin API not configured")
    return request.app.state.kc_admin_client
```

### MfaSettingsBody バリデーション

```python
from typing import Literal

class MfaSettingsBody(BaseModel):
    mfa_enabled: bool
    mfa_method: Literal["totp", "email"] = "totp"
```

### create_user MFA属性付与

```python
# admin.py create_user 内
# 既存 group + role 割当のあとに追加
if new_id and group:
    full_group = await kc.get_group(group["id"])
    group_attrs = full_group.get("attributes", {})
    mfa_enabled = group_attrs.get("mfa_enabled", ["false"])[0]
    mfa_method = group_attrs.get("mfa_method", ["totp"])[0]
    if mfa_enabled == "true":
        await kc.update_user(new_id, {
            "attributes": {
                "tenant_id": [user.tenant_id],
                "mfa_enabled": ["true"],
                "mfa_method": [mfa_method],
            },
            "requiredActions": ["CONFIGURE_TOTP"] if mfa_method == "totp" else [],
        })
```

---

## バッチ実行推奨

```
/batch 1-1~1-5   ← KeycloakAdminClient 5メソッド（Red→Green→Refactor）
/batch 2-1~2-9   ← Backend API全エンドポイント（Red→Green→Refactor）
/batch 3-1~3-4   ← Keycloak realm-export.json（手動検証）
/batch 4-1~4-6   ← Frontend全画面（一括実装）
```

---

## 注意事項

- Step 3 は `docker-compose down -v` + `docker-compose up -d` で再インポートが必要
- Step 3 完了後は P1（roles マッパー）・P2（SMTP）の再診断必須（CLAUDE.md参照）
- auth.py の `_get_kc_admin` は admin API が1回も呼ばれていないと503を返す
  → MFA無効テナント（大多数）ではmfa-statusは属性から判定するため問題ない
  → MFA有効テナントでは管理者がセキュリティ設定を保存済みのため、admin APIは初期化済み
