# 設計記録 #002 — テナントMFAポリシー管理

**日付**: 2026-03-20
**対象PRD**: Phase 3.5 (FR-030〜FR-037)
**参加者**: PM / アーキテクト / シニアエンジニア / セキュリティスペシャリスト / DBスペシャリスト

---

## 決定事項

### 1. MFA設定ストレージ（D-1）

**方式: グループ属性 + ユーザー属性ミラー**

- **グループ属性**（設定の真のソース）:
  ```json
  "/tenants/acme-corp" attributes: {
    "tenant_id": ["acme-corp"],
    "mfa_enabled": ["true"],
    "mfa_method": ["totp"]
  }
  ```
- **ユーザー属性**（認証フロー参照用のミラー）:
  ```json
  user attributes: {
    "tenant_id": ["acme-corp"],
    "mfa_enabled": ["true"],
    "mfa_method": ["totp"]
  }
  ```
- Keycloakの `conditional-user-attribute` はグループ属性を直接参照できないため、ユーザー属性にミラーリングする
- グループ属性が真のソース、ユーザー属性はAPI経由で同期

**初期値**: `mfa_enabled: false`, `mfa_method: totp`

### 2. Keycloak認証フロー設計（D-2）

**方式: 統合フロー `unified-mfa-browser` + 2段階 Conditional Authenticator**

```
unified-mfa-browser (top-level)
├── Cookie (ALTERNATIVE)
└── Forms (ALTERNATIVE)
    ├── Username/Password (REQUIRED)
    └── MFA Gate (CONDITIONAL)
        ├── Condition: mfa_enabled = true (REQUIRED)
        ├── TOTP Subflow (CONDITIONAL)
        │   ├── Condition: mfa_method = totp (REQUIRED)
        │   └── OTP Form (REQUIRED)
        └── Email OTP Subflow (CONDITIONAL)
            ├── Condition: mfa_method = email (REQUIRED)
            └── Email OTP Form (REQUIRED)
```

**authenticatorConfig**:

| alias | attribute_name | expected_value | not_set_condition |
|-------|---------------|----------------|-------------------|
| `mfa-gate-condition` | `mfa_enabled` | `true` | `skip` |
| `mfa-totp-condition` | `mfa_method` | `totp` | `skip` |
| `mfa-email-condition` | `mfa_method` | `email` | `skip` |
| `email-otp-config` | — | — | `emailOtpLength=6, expirationPeriod=300, sendAttempts=3` |

> **[FIX: セキュリティ指摘]** `mfa_enabled` のゲートチェックを `mfa_method` 分岐の外側に配置。`mfa_enabled=false` のユーザーは外側の CONDITIONAL で早期スキップされ、MFAが要求されない。

### 3. MFA方式切替フロー（D-3）

MFA設定変更API (`PUT /api/admin/security/mfa`) の処理フロー:

```
1. _require_admin(user) — 権限チェック
2. find_group_by_name(tenant_id) — テナントグループ取得
3. グループ属性を更新 (mfa_enabled, mfa_method)
4. list_users(tenant_id) — テナント全ユーザー取得
5. MFA有効化 (mfa_enabled=true):
   a. ユーザー属性 mfa_enabled, mfa_method を設定
   b. mfa_method=totp → CONFIGURE_TOTP Required Action 追加
   c. mfa_method=email → CONFIGURE_TOTP Required Action 削除
6. MFA無効化 (mfa_enabled=false):
   a. ユーザー属性 mfa_enabled を "false" に設定
   b. mfa_method は保持（再有効化用）
   c. CONFIGURE_TOTP Required Action 削除
7. 方式変更検知（既存と異なる mfa_method）:
   a. 全ユーザーのOTPクレデンシャルを一括リセット
   b. mfa_method=totp → CONFIGURE_TOTP Required Action 追加
8. 一括更新は asyncio.Semaphore(10) で並列度制御
9. レスポンス返却（部分失敗時は警告付き）
```

### 4. Backend API設計（D-4）

#### KeycloakAdminClient 追加メソッド

```python
async def get_group(self, group_id: str) -> dict[str, Any]
async def update_group_attributes(self, group_id: str, attributes: dict[str, list[str]]) -> None
async def set_user_attributes_bulk(self, user_ids: list[str], attributes: dict[str, list[str]]) -> list[str]
async def add_required_action_bulk(self, user_ids: list[str], action: str) -> list[str]
async def remove_required_action_bulk(self, user_ids: list[str], action: str) -> list[str]
```

#### Admin Router 追加エンドポイント

**GET /api/admin/security/mfa**
- 権限: `tenant_admin` / `super_admin`
- レスポンス: `{ "mfa_enabled": bool, "mfa_method": "totp" | "email" }`
- テナントグループのグループ属性から読み取り

**PUT /api/admin/security/mfa**
- 権限: `tenant_admin` / `super_admin`
- リクエスト: `{ "mfa_enabled": bool, "mfa_method": "totp" | "email" }`
- レスポンス: `{ "status": "updated", "mfa_enabled": bool, "mfa_method": str, "users_updated": int, "users_failed": int }`

#### Pydantic モデル

```python
class MfaSettingsBody(BaseModel):
    mfa_enabled: bool
    mfa_method: Literal["totp", "email"]
```

### 5. Frontend設計（D-5）

#### 新規ファイル
- `examples/react-app/src/pages/SecuritySettings.tsx` — セキュリティ設定画面

#### 変更ファイル
- `examples/react-app/src/App.tsx` — `/security` ルート追加 + AuthGuard
- `examples/react-app/src/api/adminApi.ts` — `getMfaSettings`, `updateMfaSettings` 追加
- `examples/react-app/src/pages/Dashboard.tsx` — navItems にセキュリティ設定追加
- `examples/react-app/src/pages/AdminUsers.tsx` — navItems にセキュリティ設定追加

#### SideNav構成

```
navItems:
├── ダッシュボード     (全ユーザー)
├── ユーザー管理       (tenant_admin / super_admin)
├── セキュリティ設定 ★ (tenant_admin / super_admin)
└── テナント管理       (super_admin のみ)
```

#### UI仕様

```
SecuritySettings.tsx:
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

#### 方式変更時の確認ダイアログ

```
⚠️ MFA方式の変更
MFA方式を「TOTP」→「メールOTP」に変更すると、
テナント内の全ユーザーのMFA設定がリセットされます。
各ユーザーは次回ログイン時に新しい方式でMFAを再設定する必要があります。

[キャンセル] [変更を適用]
```

#### API型定義 (adminApi.ts)

```typescript
export interface MfaSettings {
  mfa_enabled: boolean
  mfa_method: 'totp' | 'email'
}

export async function getMfaSettings(token: string): Promise<MfaSettings>
export async function updateMfaSettings(token: string, settings: MfaSettings): Promise<{ status: string; mfa_enabled: boolean; mfa_method: string; users_updated: number; users_failed: number }>
```

### 6. realm-export.json 変更（D-6）

`auth-stack/keycloak/realm-export.json` に追加:
- `authenticationFlows`: 統合MFAフロー定義（5フロー）
- `authenticatorConfig`: 条件設定（4エントリ）
- `browserFlow`: `"unified-mfa-browser"`

グループ定義の更新:
```json
{
  "name": "acme-corp",
  "path": "/tenants/acme-corp",
  "attributes": {
    "tenant_id": ["acme-corp"],
    "mfa_enabled": ["false"],
    "mfa_method": ["totp"]
  }
}
```

### 7. テナント境界セキュリティ（D-7）

| ロール | 読取 | 更新 | 対象 |
|--------|------|------|------|
| `tenant_admin` | ✅ | ✅ | 自テナントのみ |
| `super_admin` | ✅ | ✅ | 全テナント（tenant_idクエリパラメータ指定） |
| `user` | ❌ | ❌ | 403 Forbidden |

### 8. パフォーマンス設計（D-8）

- ユーザー一括更新: `asyncio.Semaphore(10)` で並列度制御
- 200ユーザー想定: 約200ms〜3秒
- 部分失敗時: 成功数・失敗数をレスポンスに含め、ログに詳細記録

---

## 却下した選択肢

| 選択肢 | 却下理由 |
|--------|---------|
| Authentication Flow動的切替 | Realm全体に影響、テナント分離不可 |
| Script Authenticator (カスタムSPI) | 保守コスト大、Keycloakアップグレードリスク |
| グループ属性のみ（ユーザー属性ミラーなし） | `conditional-user-attribute` がグループ属性を参照不可 |
| DB（PostgreSQL）にMFA設定保存 | Keycloak外部にデータ分散、整合性リスク |

---

## 成果物一覧

| ファイル | 変更種別 |
|----------|---------|
| `auth-stack/keycloak/realm-export.json` | 変更: 認証フロー追加、グループ属性追加 |
| `packages/backend-sdk/src/common_auth/services/keycloak_admin_client.py` | 変更: グループ属性CRUD、一括更新メソッド追加 |
| `packages/backend-sdk/src/common_auth/routers/admin.py` | 変更: `/security/mfa` エンドポイント追加 |
| `examples/react-app/src/pages/SecuritySettings.tsx` | 新規: セキュリティ設定画面 |
| `examples/react-app/src/App.tsx` | 変更: ルート追加 |
| `examples/react-app/src/api/adminApi.ts` | 変更: MFA API関数追加 |
| `examples/react-app/src/pages/Dashboard.tsx` | 変更: navItems追加 |
| `examples/react-app/src/pages/AdminUsers.tsx` | 変更: navItems追加 |
| `packages/backend-sdk/tests/unit/test_admin_router.py` | 変更: MFAエンドポイントテスト追加 |
