# ユーザーアカウントMFA管理

**更新日**: 2026-03-20
**対象PRD**: Phase 3.5 補足

---

## 概要

MFA設定済みユーザーが自分のMFAを管理する機能。
一般的なSaaS製品のパターンに基づき、ダッシュボードのユーザードロップダウンから
アカウント設定画面にアクセスし、MFAの確認・再設定・削除を行う。

---

## 1. 一般的なSaaS MFA管理のUI/UXパターン

| サービス | MFA管理の場所 | 操作 |
|----------|-------------|------|
| Google | アカウント設定 > セキュリティ | 確認・無効化・方式変更 |
| GitHub | Settings > Password and authentication | 確認・再設定・リカバリーコード |
| Slack | アカウント設定 > 二要素認証 | 確認・無効化 |
| AWS IAM | セキュリティ認証情報 | 確認・割当解除・再割当 |

**共通パターン**:
- ユーザープロフィール/アカウント設定内の「セキュリティ」セクション
- MFAの状態表示（有効/無効）
- 管理操作（再設定・無効化）※テナントポリシーで強制されている場合は無効化不可

---

## 2. 本プロジェクトでの設計方針

### Keycloak Account Console を活用

Keycloakは標準で **Account Console**（`/realms/{realm}/account/`）を提供しており、
ユーザーが自分のTOTP設定を管理できる。

**現状の `configureMFA` 関数**:
```typescript
// packages/frontend-sdk/src/AuthProvider.tsx
const configureMFA = useCallback(() => {
  const mfaUrl = `${authority}/account/totp`;
  window.location.href = mfaUrl;
}, [authority, user]);
```

この実装はKeycloak Account Consoleの TOTP管理ページに直接遷移する。

### 設計判断: Keycloak Account Console 委譲 + アプリ内ステータス表示

| 選択肢 | Pros | Cons |
|--------|------|------|
| **A: 完全委譲（現状）** | 実装コスト0。Keycloak標準。 | 画面遷移のUX断絶。テーマ不一致。 |
| **B: アプリ内で全実装** | 統一UX。完全制御。 | Keycloak Admin API直接操作が必要。工数大。 |
| **C: ハイブリッド（推奨）** | アプリ内でステータス表示 + 操作はKeycloak委譲。バランスがよい。 | 一部UX断絶が残る。 |

**✅ 採用: 方式C（ハイブリッド）**

---

## 3. ユーザーダッシュボードでのMFA表示

### ダッシュボードのMFAステータスカード

MFAが有効なテナントのユーザーに対して、ダッシュボードにMFAステータスを表示する。

```
/dashboard
┌──────────┬──────────────────────────────────────┐
│ SideNav  │  ダッシュボード                        │
│          │                                       │
│          │  ┌── セキュリティ ─────────────────┐  │
│          │  │                                 │  │
│          │  │  二段階認証 (MFA)                │  │
│          │  │  ✅ 有効 — TOTP（認証アプリ）    │  │
│          │  │                                 │  │
│          │  │  [設定を変更する →]               │  │
│          │  │   → Keycloak Account Console     │  │
│          │  └─────────────────────────────────┘  │
│          │                                       │
└──────────┴──────────────────────────────────────┘
```

### MFA未設定時の表示

```
│  ┌── セキュリティ ─────────────────┐  │
│  │                                 │  │
│  │  二段階認証 (MFA)                │  │
│  │  ⚠️ 未設定                      │  │
│  │  テナントポリシーで必須です。     │  │
│  │  次回ログイン時に設定が必要です。 │  │
│  │                                 │  │
│  │  [今すぐ設定する →]              │  │
│  │   → Keycloak Account Console   │  │
│  └─────────────────────────────────┘  │
```

### MFA無効テナントの表示

```
│  ┌── セキュリティ ─────────────────┐  │
│  │                                 │  │
│  │  二段階認証 (MFA)                │  │
│  │  ━ 無効（テナント設定）          │  │
│  │  管理者がMFAを有効にしていません。│  │
│  └─────────────────────────────────┘  │
```

---

## 4. UserDropdownのMFA項目

### 現状

```typescript
// Dashboard.tsx
const dropdownItems: DropdownItem[] = [
  { label: 'セキュリティ設定', icon: '🔒', onClick: configureMFA },
  { label: 'ログアウト', icon: '🚪', onClick: logout, danger: true },
]
```

### 変更後

```typescript
const dropdownItems: DropdownItem[] = [
  { label: 'アカウント設定', icon: '👤', onClick: () => navigateToAccount() },
  { label: 'ログアウト', icon: '🚪', onClick: logout, danger: true },
]
```

`アカウント設定` → Keycloak Account Console トップ (`/realms/{realm}/account/`)
- Personal Info: 名前・メール変更
- Security: パスワード変更、MFA管理、アクティブセッション

> **注意**: テナント管理者向け「セキュリティ設定」（管理画面、MFAポリシー設定）とは別。
> - 「アカウント設定」= 自分のアカウント管理（全ユーザー）→ Keycloak Account Console
> - 「セキュリティ設定」= テナントポリシー管理（admin）→ /security ページ

---

## 5. MFAステータス取得API

ダッシュボードでMFAステータスを表示するために、ユーザー自身のMFA状態を取得するAPIが必要。

### GET /api/auth/mfa-status

| 項目 | 値 |
|------|------|
| 権限 | 認証済みユーザー（全ロール） |
| レスポンス | 下記参照 |

```json
{
  "tenant_mfa_enabled": true,
  "tenant_mfa_method": "totp",
  "user_mfa_configured": true,
  "user_has_totp": true
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| `tenant_mfa_enabled` | boolean | テナントのMFAポリシーが有効か |
| `tenant_mfa_method` | string | テナントのMFA方式 ("totp" / "email") |
| `user_mfa_configured` | boolean | ユーザーがMFA設定済みか（TOTP: OTPクレデンシャル存在、Email: 常にtrue） |
| `user_has_totp` | boolean | ユーザーがTOTPクレデンシャルを持っているか |

### 実装方針

> **注意**: auth router は `prefix="/auth"` で登録されているため（setup.py）、
> デコレータは `@router.get("/mfa-status")` とする。
> Vite proxy 経由の実URL: `GET /api/auth/mfa-status`

```python
@router.get("/mfa-status", tags=["auth"])
async def get_mfa_status(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    """ユーザー自身のMFAステータスを返す"""
    kc_admin = _get_kc_admin(request)  # 共通ヘルパー（下記参照）
    # 1. ユーザー属性から mfa_enabled, mfa_method を読む
    # 2. kc_admin でユーザーのクレデンシャル一覧を取得
    # 3. OTPクレデンシャルの有無を確認
    # 4. ステータスを返す
```

### KeycloakAdminClient の共有設計

現在 `KeycloakAdminClient` は admin router のみが `_get_kc_admin()` で生成・キャッシュしている。
`mfa-status` API は auth router で提供するため、`KeycloakAdminClient` へのアクセスを共通化する。

**方針: `setup.py` で `app.state` に一元登録**

```python
# setup.py（変更）
def setup_auth(app, ...):
    # ... 既存処理 ...
    # KeycloakAdminClient を app.state に登録（全routerで共有）
    client_id = os.environ.get("KC_ADMIN_CLIENT_ID", "admin-api-client")
    client_secret = os.environ.get("KC_ADMIN_CLIENT_SECRET", "")
    if client_secret:
        app.state.kc_admin_client = KeycloakAdminClient(
            keycloak_url=config.keycloak_url,
            realm=config.keycloak_realm,
            client_id=client_id,
            client_secret=client_secret,
        )
```

```python
# 共通ヘルパー（admin.py / auth.py 両方で使用）
def _get_kc_admin(request: Request) -> KeycloakAdminClient:
    if not hasattr(request.app.state, "kc_admin_client"):
        raise HTTPException(503, "Admin API not configured")
    return request.app.state.kc_admin_client
```

これにより admin router の既存 `_get_kc_admin` も簡素化される。

---

## 6. Keycloak Account Console のカスタマイズ（将来）

### 現状（Phase 3.5）

Keycloakデフォルトの Account Console をそのまま使用。

### 将来対応（Phase 4+）

| 項目 | 対応 |
|------|------|
| テーマ統一 | Account Console に `common-auth` テーマを適用 |
| 操作制限 | テナントポリシーでMFA強制の場合、ユーザーがMFAを無効化できないようにする |
| 画面埋込 | iframe/popup でアプリ内にAccount Console を表示 |

---

## 7. 画面遷移（更新）

```
/dashboard
    │
    ├─ [MFAステータスカード]
    │   ├─ 「設定を変更する →」 → Keycloak Account Console /account/totp
    │   └─ 「今すぐ設定する →」 → Keycloak Account Console /account/totp
    │
    ├─ [UserDropdown]
    │   ├─ アカウント設定  → Keycloak Account Console /account/
    │   └─ ログアウト     → Keycloak ログアウト → /
    │
    ├─ [SideNav] セキュリティ設定 (admin)
    │   └─ /security → テナントMFAポリシー管理
    │
    └─ [SideNav] ユーザー管理 (admin)
        └─ /admin/users → ユーザー一覧・編集
```

---

## 8. 成果物一覧

| ファイル | 変更種別 |
|----------|---------|
| `packages/backend-sdk/.../routers/auth.py` | 変更: `/auth/mfa-status` エンドポイント追加 |
| `examples/react-app/src/pages/Dashboard.tsx` | 変更: MFAステータスカード追加 |
| `examples/react-app/src/api/adminApi.ts` | 変更: `getMfaStatus` API関数追加 |
| `packages/frontend-sdk/src/AuthProvider.tsx` | 検討: `configureMFA` → `openAccountConsole` にリネームまたは追加 |
| `packages/frontend-sdk/src/types.ts` | 検討: `openAccountConsole` 型追加 |

---

## 9. 却下した選択肢

| 選択肢 | 却下理由 |
|--------|---------|
| アプリ内で完全にMFA管理UI実装 | Keycloak Admin APIの直接操作（QR生成・TOTP検証）が必要で工数過大。Keycloakバージョンアップ時の互換性リスク。 |
| MFA管理を一切提供しない | ユーザーがTOTPデバイス紛失時に自己解決できない。管理者MFAリセットのみの運用は現実的でない。 |
| Keycloak Account Console をiframeで埋込 | CSP/X-Frame-Options の制約で動作しない可能性。Phase 4+で別途検討。 |
