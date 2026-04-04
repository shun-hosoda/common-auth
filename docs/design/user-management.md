# Phase 3 ユーザー管理・アクセス制御 設計書

## 1. 概要

管理者によるユーザー管理と、ロールベースのアクセス制御をカスタムReact UIで実装する。
Keycloak Admin REST APIをBackend SDK内蔵のAdmin APIでプロキシし、テナント境界を強制する。

> Admin APIはBackend SDKの `setup_auth()` で自動的に `/api/admin` にマウントされる。
> ユーザー登録は `registrationAllowed: false` のため、管理者がAdmin API経由で行う。

### 対象PRD要件

| ID | 機能 | 優先度 |
|----|------|--------|
| FR-020 | ダッシュボード画面 | Must |
| FR-021 | ログイン画面 | Must |
| FR-022 | ログアウト→リダイレクト | Must |
| FR-023 | クライアント管理（super_admin） | Must |
| FR-024 | ユーザー管理画面（tenant_admin） | Must |
| FR-025 | ユーザー登録・編集 | Must |
| FR-026 | ロールベースUI制御 | Must |
| FR-027 | Keycloak UIへの委譲 | Should |

---

## 2. ロール設計

| ロール | Keycloak対応 | 権限 |
|--------|-------------|------|
| `super_admin` | Realm-level `admin` | テナント登録・全テナントのユーザー管理・設定変更 |
| `tenant_admin` | `manage-users`（realm-management） | 自テナント内のユーザー一覧・作成・編集・無効化 |
| `user` | デフォルト（認証済み） | ログイン・プロフィール・MFA・パスワードリセット |

> **super_admin の位置づけ**: テナントを登録・管理するサービス運営者。
> 通常のKeycloakログイン画面からログインし、Dashboard経由で管理機能へアクセス。
> Keycloak管理コンソール（`/admin`）への直接アクセスは運用では使用しない。

### ロール関連 ADR

- [ADR-011](../adr/011-role-based-access-control.md): ロールベースアクセス制御設計

---

## 3. 画面遷移設計

```
/ (root)
 ├── 未ログイン → /login（Keycloakログイン画面へリダイレクト）
 └── ログイン済み → /dashboard

/dashboard [user以上]
 ├── user: プロフィール・ログアウト・MFA設定
 ├── tenant_admin: + ユーザー管理 + セキュリティ設定
 └── super_admin: + クライアント管理

/admin/users [tenant_admin以上]
 └── カスタムReact UI（Backend Admin API経由）

/admin/clients [super_adminのみ]
 └── テナント登録・管理画面

/security [tenant_admin以上]
 └── テナントMFAポリシー管理（Phase 3.5で追加）
```

---

## 4. Backend Admin API設計

### エンドポイント一覧

```
既存（/auth）:
  GET  /auth/health          → ヘルスチェック
  GET  /auth/me              → 現在ユーザー情報

Admin API（/api/admin）:
  GET    /api/admin/users              → テナント内ユーザー一覧
  POST   /api/admin/users              → ユーザー新規作成
  GET    /api/admin/users/{user_id}    → ユーザー詳細取得
  PUT    /api/admin/users/{user_id}    → ユーザー情報更新
  DELETE /api/admin/users/{user_id}    → ユーザー無効化（論理削除）
  POST   /api/admin/users/{user_id}/reset-password → PW リセット
  POST   /api/admin/users/{user_id}/reset-mfa      → MFA リセット
  GET    /api/admin/clients            → テナント一覧 (super_admin)
  POST   /api/admin/clients            → テナント作成 (super_admin)
```

### セキュリティ

- 全エンドポイントで `tenant_admin` 以上のロールをJWTから検証
- `tenant_id` クレームでテナント境界を強制フィルタリング
- Keycloak Admin REST APIをプロキシ（フロントから直接叩かない）
- Rate Limiting適用

### Keycloak Admin API認証方式

```
認証フロー: OAuth 2.0 client_credentials grant
Client ID:  admin-api-client (Confidential Client)
Client認証: client_id + client_secret
スコープ:   realm-management (manage-users 等)
```

```
[Frontend]  →  [Backend Admin API]  →  [Keycloak Admin REST API]
  JWT(user)     ① JWTからrole/tenant_id検証
                ② client_credentialsトークンで
                   Keycloak Admin APIを呼び出し
                ③ tenant_id境界フィルタ適用
```

- `client_secret` は環境変数（`KC_ADMIN_CLIENT_SECRET`）で管理
- トークンキャッシュ + 有効期限前自動更新

---

## 5. Frontend SDK拡張

### useAuth Hook追加

```typescript
interface AuthContextValue {
  // 認証状態
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  
  // 認証操作
  login: () => Promise<void>;
  logout: () => Promise<void>;
  register: () => void;
  resetPassword: () => void;
  configureMFA: () => void;
  handleCallback: () => Promise<void>;
  
  // トークン・ロール
  getAccessToken: () => string | null;
  hasRole: (role: string) => boolean;
}
```

### AuthGuard

```typescript
interface AuthGuardProps {
  children: ReactNode;
  requiredRoles?: string[];         // ロール要件（OR条件）
  fallback?: ReactNode;             // ローディング中の表示
  onUnauthenticated?: () => void;   // 未認証時のコールバック
  unauthorizedFallback?: ReactNode; // 権限不足時の表示
}
```

> フロントのRBACはUI制御のみ。API側でも必ずバックエンド検証を行う。

---

## 6. Keycloak Theme カスタマイズ

### 設計原則

1. **CSSのみ**: `.ftl` テンプレートの構造変更は最小限
2. **CSS変数ベース**: 顧客ごとにCSSファイルのみ差し替え
3. **Keycloakバージョン互換性**: テンプレート構造に依存しない

### テーマ構成

```
auth-stack/keycloak/themes/
└── common-auth/
    └── login/
        ├── theme.properties
        └── resources/css/styles.css
```

### CSS変数定義

```css
:root {
  --primary-color: #2563eb;
  --primary-hover: #1d4ed8;
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-color: #1e293b;
  --border-radius: 8px;
  --logo-url: none;
}
```

顧客別カスタマイズ: CSS変数の値を上書きするだけでロゴ・カラー・背景を変更可能。
`.ftl` ファイル編集は禁止（Keycloakアップデート時のログイン不能リスク回避）。

---

## 7. Keycloak設定変更

- Realm Role追加: `super_admin`, `tenant_admin`
- テストユーザー: `admin_acme-corp@example.com`（tenant_admin）, `admin_globex-inc@example.com`（tenant_admin）
- `super_admin` ロールは定義済みだがテストユーザーには未割り当て（運用時に手動付与）
- `admin-api-client`（Confidential Client）: Service Account Roles で `realm-admin` 付与
- Client Theme: `loginTheme: "common-auth"`
- `registrationAllowed: false`（ユーザー登録は管理者がAdmin API経由で実施）
- `VERIFY_EMAIL` defaultAction: `false`

## 8. DB設計

ロール情報はKeycloakが管理する。
アプリ側DB（app-db）にはグループ・権限管理テーブルを追加済み:
`tenant_groups`, `user_group_memberships`, `permissions`, `group_permissions`, `user_permissions`
（RLSで `tenant_id` 分離済み）。

---

## 9. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-010](../adr/010-user-management-ui-delegation.md) | カスタムReact実装（Keycloak委譲から変更） |
| [ADR-011](../adr/011-role-based-access-control.md) | ロールベースアクセス制御 |

---

*元ログ: [設計会議記録 — Phase 3: ユーザー管理・アクセス制御](logs/2026-03-01_phase3-user-management.md)*

---

## 10. Phase 4 — ユーザー招待フロー設計

> 設計会議: 2026-04-04 / レビュー指摘M-1〜M-8 修正済み

### 10.1 設計方針（アーキテクチャ決定）

| 項目 | 決定 | 理由 |
|------|------|------|
| KCユーザー作成タイミング | **承諾時（Option A: 遅延作成）** | Keycloakをクリーンに保つ。招待未承諾ユーザーがKCに残らない |
| トークン管理 | **自前DB (`invitation_tokens`)** | Keycloak Required Actionsに依存せずポータビリティを維持 |
| Race condition対策 | **`SELECT FOR UPDATE`** | 同トークンの二重承諾を防止 |
| Public APIのRate Limit | **既存Middlewareを適用** | validate: 10req/min, accept: 5req/min per IP |
| 直接ユーザー作成API | **`POST /api/admin/users` を維持** | APIは残す。UIボタンは将来の判断に委ねる |
| メール送信 | **Backend SDK内 EmailService（SMTP直接）** | M-1: Keycloakは任意メール送信不可のため自前実装 |
| MFA設定タイミング | **Keycloak Required Action（ログイン後）** | M-4: 承諾時に `CONFIGURE_TOTP` をKC userに付与。テナントMFA=OFFなら付与しない |
| 一括招待失敗方針 | **Best-effort（成功/失敗を個別返却）** | M-6: 全件ロールバックはUXが悪化するため |
| Public API DB接続 | **RLSバイパス用サービスアカウント接続** | S-6: accept/validate時は `app.current_tenant_id` がセットされないためRLSを使わない専用接続を使用 |

### 10.2 ルーター構成（M-3修正）

```
packages/backend-sdk/src/common_auth/routers/
  auth.py        → /auth/*          (JWT認証必須)
  admin.py       → /api/admin/*     (tenant_admin以上)
  invitation.py  → /api/invitations/* (Public + Rate Limited) ← 新規追加
```

`setup.py` への追加:

```python
from common_auth.routers.invitation import router as invitation_router

# JWTAuthMiddleware の除外パスに追加
EXCLUDED_PATHS = ["/auth/health", "/api/invitations/validate", "/api/invitations/accept"]

app.include_router(invitation_router, prefix="/api/invitations", tags=["invitations"])
```

### 10.3 EmailService 設計（M-1修正）

```python
# packages/backend-sdk/src/common_auth/services/email_service.py

class EmailService:
    """SMTP経由で招待メールを送信するサービス。
    Keycloakは任意メール送信不可のため、BackendのSMTP直接送信で実装する。
    設定は AuthConfig の smtp_* 環境変数から読み込む。
    """
    def __init__(self, smtp_host: str, smtp_port: int, from_addr: str): ...

    async def send_invitation(
        self,
        to_email: str,
        token: str,
        invited_by_name: str,
        tenant_name: str,
        base_url: str,
        custom_message: str | None = None,
    ) -> None:
        """
        招待URLを含むメールを送信する。
        URL例: https://{base_url}/invite/accept?token={token}
        """
```

環境変数（`AuthConfig` に追加):

```env
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=noreply@example.com
INVITATION_BASE_URL=http://localhost:5173   # 招待URLのベースURL
INVITATION_EXPIRES_HOURS=72                # デフォルト有効期限（最大168h）
```

### 10.4 DBコネクション依存注入（M-2修正）

Public Endpoint（invitation.py）では `app.state.db_pool` を FastAPI Dependency 経由で取得する。

```python
# packages/backend-sdk/src/common_auth/dependencies/db.py

from fastapi import Depends, HTTPException, Request, status
import asyncpg

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """app.state.db_pool を返す。未設定なら503。"""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured (APP_DATABASE_URL missing)",
        )
    return pool

async def get_db_conn_bypass_rls(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> asyncpg.Connection:
    """
    RLSバイパス用コネクション（Public API専用）。
    S-6修正: accept/validate は tenant_id コンテキストがないためRLSバイパスが必要。
    専用のDB Roleを使用するか、SET LOCAL row_security = off での接続を想定。
    """
    ...
```

### 10.5 APIエンドポイント詳細

#### 管理者側（認証必須: tenant_admin以上）

```
POST   /api/admin/invitations               招待発行（最大50件一括）
GET    /api/admin/invitations               招待一覧（pending/expired含む全件）
DELETE /api/admin/invitations/{id}          招待取消（status → revoked）
POST   /api/admin/invitations/{id}/resend   招待再送（旧トークン失効 → 新トークン発行）
```

**resend フロー（S-4修正）:**

```python
# POST /api/admin/invitations/{id}/resend
async def resend_invitation(id):
    # 1. 既存レコードを status='revoked', revoked_at=NOW() に更新
    # 2. 同メール・同テナントで新 invitation_tokens レコードを INSERT
    #    （uq_invitation_pending 制約: 旧レコードは revoked なので重複しない）
    # 3. 新トークンで招待メールを再送信
```

**一括招待レスポンス（M-6修正: Best-effort）:**

```python
class InvitationBulkResponse(BaseModel):
    succeeded: list[InvitationResponse]   # 成功した招待
    failed: list[InvitationFailedItem]    # 失敗した招待

class InvitationFailedItem(BaseModel):
    email: str
    reason: str   # "already_member" | "pending_exists" | "smtp_error" | ...
```

**重複チェック仕様（M-5修正）:**

```python
# POST /api/admin/invitations 内の重複チェック
# 1. invitation_tokens に pending レコードが存在 → 409 / failed に追加
# 2. Keycloak に既存ユーザーとして存在するか確認:
#    GET /admin/realms/{realm}/users?email={email}&exact=true
#    → 該当テナントのユーザーなら → "already_member" でfailedに追加
```

#### 招待受諾側（Public + Rate Limited）

```
GET    /api/invitations/validate?token=xxx  トークン検証（無効/期限切れは全て404）
POST   /api/invitations/accept              招待承諾（PW設定 + KC User作成）
```

**accept 処理フロー（M-2, M-4修正）:**

```python
async def accept_invitation(body: InvitationAcceptRequest, db = Depends(get_db_conn_bypass_rls)):
    # 1. SELECT FOR UPDATE でトークンをロック（race condition防止）
    # 2. status='pending' AND expires_at > NOW() チェック → 失敗なら404
    # 3. Keycloak: ユーザー作成
    #    payload = {
    #      "username": email,
    #      "email": email,
    #      "enabled": True,
    #      "emailVerified": True,     ← 招待経由なので確認済み扱い
    #      "firstName": display_name,
    #      "requiredActions": ["CONFIGURE_TOTP"] if mfa_enabled else []  ← M-4
    #    }
    # 4. Keycloak: パスワード設定（temporary=False）
    #    → KC PW Policy 違反時は 422 でエラー詳細をフロントに返す（S-5）
    # 5. Keycloak: ロール付与（invitation_tokens.role に従う）
    # 6. DB (bypass_rls): user_profiles に INSERT
    # 7. DB: tenant_groups にメンバー追加（group_id があれば）
    # 8. DB: invitation_tokens.status='accepted', accepted_at=NOW()
    # 9. コミット
```

### 10.6 フロントエンド画面仕様

| 画面 | パス | 認証 |
|------|------|------|
| 招待発行 | `/admin/users/invite` | tenant_admin以上 |
| 招待一覧管理 | `/admin/invitations` | tenant_admin以上 |
| 招待承諾 | `/invite/accept?token=xxx` | 不要（Public） |

**招待承諾画面のセキュリティ要件（S-1修正）:**

```html
<!-- /invite/accept ページのHTMLに必須 -->
<meta name="referrer" content="no-referrer">
```

**承諾完了後の画面遷移（S-7修正）:**

```
承諾完了
  ├── テナントMFA = OFF → 完了画面 + [ログインする] ボタン → Keycloakログイン画面へ
  └── テナントMFA = ON  → 完了画面 + [ログインしてMFAを設定する] ボタン
                          → Keycloakログイン → CONFIGURE_TOTP Required Action が自動表示
```

**パスワード入力UX（S-8修正）:**  
承諾画面のパスワード入力欄の下に Keycloak PW Policy 要件を表示する。  
（例: 「8文字以上、英数字を含む必要があります」）  
要件文は環境変数 `KEYCLOAK_PW_POLICY_HINT` で設定可能にする。

### 10.7 URLクエリトークンのリスク（S-2: ADR記録）

招待URLは `?token=xxxx` 形式でクエリパラメータにトークンを含む。  
業界標準（Linear, GitHub等）でも同方式を採用しており、リスクは許容済みとする。

リスク内容と対策:
- サーバーアクセスログ → WAF/プロキシ設定で `/invite/accept` クエリのログ除外を推奨
- ブラウザ履歴 → トークン承諾後は即座に `status='accepted'` にするため再利用不可
- Referrerヘッダ → `<meta name="referrer" content="no-referrer">` で対策済み（S-1参照）

### 10.8 承諾フロー 部分失敗の補償処理（NEW-1）

`POST /api/invitations/accept` でKeycloakユーザー作成後にDBトランザクションが失敗した場合、
Keycloakにユーザーが残留する。これにより次回招待時に「already_member」エラーになる。

**補償処理の実装方針:**

```python
# routers/invitation.py — accept_invitation 内
kc_user_id: str | None = None
try:
    # Step 3: KC User 作成
    kc_user_id = await kc.create_user(payload)

    # Step 4-8: PW設定・ロール付与・DB更新...
    # （Keycloak操作はロールバック不可のため先に完了させる）
    await kc.reset_password(kc_user_id, body.password, temporary=False)
    await kc.assign_realm_role(kc_user_id, invitation["role"])
    # DB操作 ...
    await conn.execute("UPDATE invitation_tokens SET status='accepted' ...")

except Exception:
    # 補償処理: KC Userが作成済みであれば削除して整合性を回復
    if kc_user_id:
        try:
            await kc.delete_user(kc_user_id)
            logger.info("Compensated: deleted KC user %s after accept failure", kc_user_id)
        except Exception as kc_err:
            # 補償処理も失敗した場合は警告ログのみ（手動対応が必要）
            logger.error(
                "COMPENSATION FAILED: KC user %s was not deleted. Manual cleanup required. Error: %s",
                kc_user_id, kc_err,
            )
    raise
```

`KeycloakAdminClient` に `delete_user` メソッドを追加する（既存には未実装）:

```python
async def delete_user(self, user_id: str) -> None:
    """Delete a Keycloak user (used for compensation on accept failure)."""
    resp = await self._request("DELETE", f"/users/{user_id}")
    if resp.status_code not in (204, 404):
        resp.raise_for_status()
```

### 10.9 承諾API でのMFAポリシー取得（NEW-2）

`POST /api/invitations/accept` はPublic APIのためJWTが存在しない。
テナントMFA設定を取得するには `KeycloakAdminClient` 経由でKeycloakグループ属性を直接参照する。

**実装方針:**

```python
# accept_invitation 内 — グループ属性からMFAポリシーを取得
group = await kc.find_group_by_name(invitation["tenant_id_str"])
    # tenant_id_str: invitation_tokens JOIN tenants から取得した realm_name
mfa_enabled = False
mfa_method = "totp"
if group:
    full_group = await kc.get_group(group["id"])
    attrs = full_group.get("attributes") or {}
    mfa_enabled = attrs.get("mfa_enabled", ["false"])[0] == "true"
    mfa_method = attrs.get("mfa_method", ["totp"])[0]

# Keycloakユーザー作成 payload にMFA設定を反映
required_actions = []
if mfa_enabled and mfa_method == "totp":
    required_actions = ["CONFIGURE_TOTP"]

payload = {
    ...
    "requiredActions": required_actions,
    "attributes": {
        "tenant_id": [invitation["tenant_id_str"]],
        "mfa_enabled": [str(mfa_enabled).lower()],
        "mfa_method": [mfa_method],
    },
}
```

DBの `invitation_tokens` に `tenant_id`（UUID）は持っているが、Keycloakグループ名は `realm_name`（文字列）なので、`tenants` テーブルの `realm_name` を JOINして取得する。
