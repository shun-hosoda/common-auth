# Backend SDK 設計補足

このドキュメントはBackend SDK実装時の詳細仕様を補足する。

## 環境変数バリデーション

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
