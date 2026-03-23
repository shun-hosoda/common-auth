# Backend SDK 設計書

Backend SDKの実装仕様。Rate Limiting、JWT認証、RLS、SMTP設定を含む。

---

## 1. 環境変数

### 必須環境変数

Backend SDKは起動時（`setup_auth(app, config)`実行時）に以下をチェックする。

| 環境変数 | 必須 | 説明 | デフォルト値 |
|---------|-----|------|------------|
| `KEYCLOAK_URL` | ✅ | Keycloak URL | なし |
| `KEYCLOAK_REALM` | ✅ | Realm名 | なし |
| `KEYCLOAK_CLIENT_ID` | ✅ | Client ID | なし |
| `TENANT_ID_SOURCE` | ❌ | tenant_id抽出方法 | `iss` |
| `TENANT_ID_CLAIM` | ❌ | カスタムクレーム名 | なし |
| `TENANT_ID_FIXED` | ❌ | 固定tenant_id | なし |
| `JWKS_CACHE_TTL` | ❌ | JWKSキャッシュTTL（秒） | `86400` (24時間) |
| `ENABLE_RLS` | ❌ | RLS用セッション設定 | `true` |
| `RATE_LIMIT_ENABLED` | ❌ | Rate Limiting有効化 | `true` |
| `RATE_LIMIT_DEFAULT_REQUESTS` | ❌ | デフォルト制限（/min） | `60` |
| `RATE_LIMIT_LOGIN_REQUESTS` | ❌ | ログイン制限（/min） | `5` |

### バリデーションエラーメッセージ

```python
# 環境変数不足の例
ConfigurationError: KEYCLOAK_URL is required. Set the environment variable or provide it in AuthConfig.

# 形式エラーの例
ConfigurationError: KEYCLOAK_URL must be a valid URL. Got: 'not-a-url'

# 矛盾の例
ConfigurationError: TENANT_ID_SOURCE='custom' requires TENANT_ID_CLAIM to be set.
```

### 実装例

```python
from common_auth import AuthConfig, ConfigurationError

try:
    config = AuthConfig.from_env()
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)
```

## エラーハンドリング

### エラー分類と HTTPステータスコード

| エラーカテゴリ | HTTPステータス | error | 発生タイミング |
|---|---|---|---|
| 認証ヘッダなし | 401 | `unauthorized` | Authorizationヘッダ欠如 |
| トークン形式不正 | 401 | `unauthorized` | Bearer形式でない、不正なJWT |
| トークン検証失敗 | 401 | `unauthorized` | 署名不一致、有効期限切れ |
| 権限不足 | 403 | `forbidden` | ロール/スコープ不足（オプション機能） |
| Keycloak接続失敗 | 503 | `service_unavailable` | JWKS取得失敗 |
| 内部エラー | 500 | `internal_server_error` | 予期しない例外 |

### エラーレスポンス形式

```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token",
  "detail": "Token signature verification failed"  // 開発環境のみ
}
```

### ミドルウェア実装パターン

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def jwt_auth_middleware(request: Request, call_next):
    try:
        # JWT検証処理
        token = extract_token(request)
        user = await verify_token(token)
        request.state.user = user
        
        # RLS設定（ENABLE_RLS=trueの場合）
        if config.enable_rls:
            await set_tenant_id(user.tenant_id)
        
        response = await call_next(request)
        return response
        
    except MissingAuthorizationHeader:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Missing authorization header"}
        )
    except InvalidTokenFormat:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Invalid token format"}
        )
    except TokenExpired:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Token expired"}
        )
    except KeycloakUnavailable:
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "message": "Authentication service unavailable"}
        )
    except Exception as e:
        logger.exception("Unexpected error in auth middleware")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "message": "Internal server error"}
        )
```

## RLSセッション設定

### PostgreSQL セッション変数の設定

Backend SDKは各リクエストで以下を実行する（`ENABLE_RLS=true`時）:

```python
async def set_tenant_id(tenant_id: str):
    """
    PostgreSQL セッション変数を設定してRLSポリシーに適用する。
    SET LOCAL を使用することで、トランザクション終了時に自動クリアされる。
    """
    async with db_session() as session:
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
```

### RLS無効化時の挙動

`ENABLE_RLS=false`の場合:
- セッション変数の設定をスキップ
- ミドルウェアのみでtenant_idフィルタリング（ADR-006のリスクあり）

### テスト例

```python
@pytest.mark.asyncio
async def test_rls_enforcement():
    """RLSによるテナント分離が機能することを確認"""
    # Arrange
    tenant_a = create_tenant("tenant-a")
    tenant_b = create_tenant("tenant-b")
    user_a = create_user(tenant_a.id, "user-a")
    user_b = create_user(tenant_b.id, "user-b")
    
    # Act: tenant-aのトークンでtenant-bのユーザーにアクセス
    token = create_jwt(tenant_id=tenant_a.id, sub=user_a.id)
    response = await client.get(
        f"/api/users/{user_b.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert: RLSにより404を返す（存在しないように見える）
    assert response.status_code == 404
```

## ロギング戦略

### ログレベルと出力内容

| レベル | 状況 | 出力内容 |
|---|---|---|
| INFO | 正常な認証成功 | `Authenticated user={sub} tenant={tenant_id}` |
| WARNING | トークン期限切れ | `Token expired for user={sub}` |
| WARNING | JWKS取得失敗（キャッシュ利用） | `JWKS refresh failed, using cached keys` |
| ERROR | JWKS取得失敗（キャッシュ切れ） | `JWKS unavailable, cannot verify tokens` |
| ERROR | 設定エラー | `Configuration error: KEYCLOAK_URL is required` |

### 機密情報の除外

- JWT本体をログに出力しない（kidとalgのみ）
- エラーメッセージにトークンの内容を含めない

## パフォーマンス考慮

### JWKSキャッシュ

- インメモリキャッシュ（`cachetools.TTLCache`）
- TTLデフォルト24時間、環境変数で調整可能
- マルチプロセス環境では各プロセスが独立キャッシュ（共有不要）

### RLS設定のオーバーヘッド

- `SET LOCAL`は軽量操作（< 1ms）
- トランザクション単位で自動クリア、手動管理不要

## セキュリティ考慮事項

### トークンの取り扱い

- メモリ保持のみ（DB/ファイルに保存しない）
- リクエストスコープで破棄

### エラーメッセージの情報漏洩対策

- 本番環境では`detail`フィールドを返さない
- 攻撃者にシステム内部情報を与えない

### Rate Limiting（Phase 2）

IPベースのリクエスト制限:
- デフォルト: 100 req/min per IP
- `/auth/login`等の認証エンドポイントは厳格化（10 req/min）

---

## 7. Rate Limiting Middleware

### 設計方針

- アルゴリズム: Token Bucket方式（[ADR-007](../adr/007-rate-limiting-strategy.md)）
- ストレージ: メモリキャッシュ（`cachetools.TTLCache`）
- 抽象化: `RateLimitStore` インターフェースで将来のRedis対応に備える

### クラス設計

**ファイル**: `packages/backend-sdk/src/common_auth/middleware/rate_limit.py`

```python
class RateLimitStore(ABC):
    """Rate limiting状態を管理するストレージの抽象クラス。"""
    
    @abstractmethod
    def check_and_increment(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Args:
            key: クライアント識別子（通常はIP）
            limit: 制限値（リクエスト数）
            window: 時間窓（秒）
        Returns:
            (許可/拒否, 残りリクエスト数)
        """
        pass


class InMemoryRateLimitStore(RateLimitStore):
    """メモリベースのRate Limitingストレージ（単一インスタンス用）。"""
    
    def __init__(self, maxsize: int = 10000):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=60)
        self._lock = threading.Lock()
    
    def check_and_increment(self, key, limit, window):
        with self._lock:
            current = self._cache.get(key, 0)
            if current >= limit:
                return (False, 0)
            self._cache[key] = current + 1
            return (True, limit - (current + 1))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token Bucket方式のRate Limiting Middleware。"""
    
    def __init__(self, app, config: AuthConfig, store: RateLimitStore | None = None):
        super().__init__(app)
        self.config = config
        self.store = store or InMemoryRateLimitStore()
    
    async def dispatch(self, request, call_next):
        if not self.config.rate_limit_enabled:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        path = request.url.path
        limit = self.limits.get(path, self.limits["default"])
        key = f"ratelimit:{client_ip}:{path}"
        allowed, remaining = self.store.check_and_increment(key, limit, 60)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "too_many_requests"},
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(limit)}
            )
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
```

### 制限値

| エンドポイント | 制限値 | 理由 |
|--------------|--------|------|
| `/auth/login` | 5 req/min | ブルートフォース対策 |
| その他API | 60 req/min | API abuse防止 |

### ストレージロードマップ

| Phase | ストレージ | 対応 |
|-------|----------|------|
| Phase 2a | `InMemoryRateLimitStore` | 単一インスタンス |
| Phase 3 | `RedisRateLimitStore` | 水平スケール対応 |

---

## 8. Keycloak Realm設定拡張

**ファイル**: `auth-stack/keycloak/realm-export.json`

### 追加設定

```json
{
  "registrationAllowed": true,
  "registrationEmailAsUsername": true,
  "verifyEmail": true,
  "resetPasswordAllowed": true,
  "otpPolicyType": "totp",
  "otpPolicyAlgorithm": "HmacSHA1",
  "otpPolicyDigits": 6,
  "otpPolicyPeriod": 30,
  "passwordPolicy": "length(8) and digits(1) and lowerCase(1) and upperCase(1)"
}
```

### Required Actions

| alias | 用途 | defaultAction |
|-------|------|---------------|
| `VERIFY_EMAIL` | メール確認 | true |
| `CONFIGURE_TOTP` | MFA設定（任意） | false |

> MFAはPhase 2では任意設定。テナント単位の強制ポリシーは [Phase 3.5 MFA設計](auth/mfa/tenant-policy.md) で対応。

---

## 9. SMTP設定

### 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|----------|
| `SMTP_HOST` | SMTPホスト | `mailhog`（開発環境） |
| `SMTP_PORT` | SMTPポート | `1025` |
| `SMTP_FROM` | 送信元アドレス | `noreply@example.com` |
| `SMTP_AUTH` | SMTP認証有無 | `false` |
| `SMTP_USER` | SMTPユーザー | — |
| `SMTP_PASSWORD` | SMTPパスワード | — |

### シークレット管理ルール

- `.env.example` にはプレースホルダーのみ記載
- 実際のシークレット値を含む `.env` は `.gitignore` に追加
- 本番環境: AWS Secrets Manager / Azure Key Vault / HashiCorp Vault を推奨

---

## 10. MFA (TOTP) / パスワードリセット / セルフ登録

### MFA (TOTP)

- Keycloak標準のTOTP（RFC 6238準拠）
- `CONFIGURE_TOTP` Required Action で初回設定
- ユーザー体験: 初回ログイン後にQRコード表示 → Google Authenticator等でスキャン

### パスワードリセット

1. ユーザーが「パスワードを忘れた」をクリック
2. Keycloakがリセットリンク付きメール送信
3. ユーザーがリンクから新パスワード入力
4. 完了後、全セッション無効化

- リセットトークン有効期限: 12時間、1回のみ使用可能

### ユーザーセルフ登録

1. ユーザーが登録フォーム入力 → Keycloakが確認メール送信 → メール確認でアカウント有効化
- メール確認必須（`verifyEmail: true`）
- パスワードポリシー: 最小8文字、大小英字・数字を含む

---

## 11. セキュリティ対策まとめ

| 脅威 | 対策 |
|------|------|
| ブルートフォース攻撃 | Rate Limiting（5 req/min for login） |
| クレデンシャルスタッフィング | Rate Limiting + パスワードポリシー |
| API abuse | Rate Limiting（60 req/min default） |
| X-Forwarded-For偽装 | 信頼プロキシCIDR設定 |
| メール列挙 | エラーメッセージ統一 |
| SMTP資格情報漏洩 | 環境変数管理 + `.gitignore` |
| トークン漏洩 | メモリ保持のみ、DB/ファイル保存禁止 |
| システム情報漏洩 | 本番ではdetailフィールド非返却 |

## 12. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-004](../adr/004-pyjwt-for-backend-jwt-verification.md) | PyJWT + cryptography |
| [ADR-006](../adr/006-defense-in-depth-rls.md) | 多層防御RLS |
| [ADR-007](../adr/007-rate-limiting-strategy.md) | Token Bucket方式 |
| [ADR-009](../adr/009-email-delivery-method.md) | Keycloak内蔵SMTP |

---

*元ログ: [設計会議記録 — Phase 2 機能拡張](logs/2026-03-01_190131_phase2-features.md)*
