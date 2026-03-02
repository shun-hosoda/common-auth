# 実装計画 — Phase 2a: Rate Limiting + Auth Stack拡張

**日時**: 2026-03-01 20:13  
**対象**: Phase 2a（Must実装）

## 参加者

- Architect
- Senior Engineer
- Security Specialist
- DB Specialist
- Product Manager
- **ドメインペルソナ**: 認証基盤 / IDaaS、複数プロジェクトを持つソフトウェア開発企業

## 実装スコープ

### 新規作成ファイル

**Backend SDK**:
- `packages/backend-sdk/src/common_auth/middleware/rate_limit.py`
- `packages/backend-sdk/tests/unit/test_rate_limit.py`
- `packages/backend-sdk/tests/integration/test_rate_limit_integration.py`

**Auth Stack**: （既存ファイルの更新）

### 修正ファイル

**Backend SDK**:
- `packages/backend-sdk/src/common_auth/config.py` - 設定項目追加
- `packages/backend-sdk/src/common_auth/__init__.py` - エクスポート追加
- `packages/backend-sdk/src/common_auth/setup.py` - Middleware追加
- `packages/backend-sdk/README.md` - Rate Limiting使用例追加

**Auth Stack**:
- `auth-stack/.env.example` - SMTP設定追加
- `auth-stack/keycloak/realm-export.json` - MFA/登録/SMTP設定
- `auth-stack/docker-compose.yml` - 環境変数追加
- `auth-stack/README.md` - SMTP設定手順追加

## 実装方針

### アーキテクチャ

**抽象化層の導入**:
```python
RateLimitStore (ABC)
    ↓ 実装
InMemoryRateLimitStore (Phase 2a)
RedisRateLimitStore (Phase 3)
```

**Middleware統合**:
```python
FastAPI App
  ↓ add_middleware
SecurityHeadersMiddleware (既存)
  ↓
RateLimitMiddleware (新規)
  ↓
JWTAuthMiddleware (既存)
  ↓
TenantMiddleware (既存)
  ↓
Application Logic
```

**設計パターン**:
- Strategy Pattern: `RateLimitStore`の切り替え可能性
- Dependency Injection: Middlewareが`RateLimitStore`を受け取る
- Template Method: `RateLimitStore`の抽象メソッド

### コーディング規約

**Python標準準拠**:
- PEP 8（snake_case、private変数は`_`prefix）
- 型ヒント必須（Python 3.11+対応）
- Docstring（Google Style）

**関数サイズ**:
- 基本30行以内
- Middlewareの`dispatch`は例外（複雑なロジック含む）

**エラーハンドリング**:
- 予期しないエラーはログ出力してgraceful degradation
- Rate Limit超過は429レスポンス（エラーではない）

**ロギング**:
- `logging`モジュール使用
- レベル: DEBUG（詳細フロー）、INFO（キャッシュヒット/ミス）、WARNING（キャッシュ満杯）、ERROR（予期しないエラー）

### テスト戦略

**TDD（Test-Driven Development）**:
- Red → Green → Refactorサイクルを厳守
- テストを先に書き、失敗を確認してから実装

**テストレベル**:
| レベル | 対象 | ツール | カバレッジ目標 |
|--------|------|--------|----------------|
| 単体 | `InMemoryRateLimitStore` | pytest + Mock | 95%+ |
| 統合 | `RateLimitMiddleware` | FastAPI TestClient | 90%+ |
| E2E | Auth Stack + Example App | 手動テスト | - |

**テストケース**:
1. 制限値以下のリクエスト → 200 OK + X-RateLimit-Remainingヘッダー
2. 制限値超過 → 429 Too Many Requests + Retry-Afterヘッダー
3. X-Forwarded-For（信頼プロキシ） → 最初のIPを使用
4. X-Forwarded-For（非信頼プロキシ） → 無視
5. エンドポイント別制限（/auth/login vs その他）
6. キャッシュ満杯時の警告ログ
7. Rate Limiting無効化（`rate_limit_enabled=False`）

## 実装順序

### Step 1: Rate Limiting基盤（抽象化層）

**1-1. RateLimitStore抽象クラス定義**
```python
from abc import ABC, abstractmethod

class RateLimitStore(ABC):
    """Rate Limiting状態を管理するストレージの抽象クラス。"""
    
    @abstractmethod
    def check_and_increment(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int]:
        """
        レート制限をチェックし、カウンターを増分する。
        
        Args:
            key: クライアント識別子（通常はIP）
            limit: 制限値（リクエスト数）
            window: 時間窓（秒）
        
        Returns:
            (許可/拒否, 残りリクエスト数)
        """
        pass
```

**1-2. InMemoryRateLimitStore実装**

[Red] テスト:
```python
def test_check_and_increment_under_limit():
    store = InMemoryRateLimitStore(maxsize=100)
    allowed, remaining = store.check_and_increment("192.168.1.1", limit=5, window=60)
    assert allowed is True
    assert remaining == 4

def test_check_and_increment_over_limit():
    store = InMemoryRateLimitStore(maxsize=100)
    for _ in range(5):
        store.check_and_increment("192.168.1.1", limit=5, window=60)
    
    allowed, remaining = store.check_and_increment("192.168.1.1", limit=5, window=60)
    assert allowed is False
    assert remaining == 0
```

[Green] 実装

[Refactor] スレッドセーフ確認、キャッシュ満杯警告ログ追加

### Step 2: Rate Limiting Middleware

**2-1. RateLimitMiddleware実装**

[Red] テスト: 制限超過時429
```python
@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(test_app):
    # 5回リクエスト（制限値）
    for _ in range(5):
        response = test_app.get("/auth/login")
        assert response.status_code in [200, 401]  # 認証は別問題
    
    # 6回目で429
    response = test_app.get("/auth/login")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
```

[Green] 実装

[Refactor] X-Forwarded-For検証追加

**2-2. X-Forwarded-For検証**

[Red] テスト:
```python
def test_trusted_proxy_uses_forwarded_ip():
    config = AuthConfig(
        rate_limit_trusted_proxies=["10.0.0.0/8"]
    )
    # X-Forwarded-For: 203.0.113.1 (実際のクライアント)
    # request.client.host: 10.0.0.5 (信頼プロキシ)
    # → 203.0.113.1 をクライアントIPとして使用
    
def test_untrusted_proxy_ignores_forwarded():
    config = AuthConfig(
        rate_limit_trusted_proxies=["10.0.0.0/8"]
    )
    # X-Forwarded-For: 203.0.113.1
    # request.client.host: 192.168.1.100 (非信頼プロキシ)
    # → 192.168.1.100 をクライアントIPとして使用
```

[Green] 実装（`ipaddress`モジュール使用）

[Refactor] エラーハンドリング強化

### Step 3: 設定拡張

**3-1. AuthConfig更新**

```python
# common_auth/config.py
class AuthConfig(BaseSettings):
    # ... 既存フィールド ...
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(
        default=True, 
        description="Enable rate limiting"
    )
    rate_limit_default_requests: int = Field(
        default=60, 
        ge=1, 
        description="Default requests per minute"
    )
    rate_limit_login_requests: int = Field(
        default=5, 
        ge=1, 
        description="Login requests per minute"
    )
    rate_limit_trusted_proxies: list[str] = Field(
        default_factory=list, 
        description="Trusted proxy CIDR ranges"
    )
```

**3-2. __init__.py更新**

```python
# common_auth/__init__.py
from .middleware.rate_limit import RateLimitMiddleware, RateLimitStore
```

**3-3. setup.py更新**

```python
def setup_auth(
    app: FastAPI, 
    config: AuthConfig,
    rate_limit_store: RateLimitStore | None = None
):
    # Rate Limiting（最初に追加、すべてのリクエストに適用）
    if config.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware, 
            config=config,
            store=rate_limit_store
        )
    
    # Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # JWT Auth
    app.add_middleware(JWTAuthMiddleware, config=config)
    
    # Tenant Context
    app.add_middleware(TenantMiddleware, config=config)
    
    # Auth Router
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
```

### Step 4: Auth Stack設定

**4-1. .env.example更新**

```bash
# ===================================
# SMTP Settings (Phase 2)
# ===================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=noreply@example.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Gmail: https://support.google.com/accounts/answer/185833
```

**4-2. realm-export.json更新**

MFA、パスワードリセット、ユーザー登録、SMTP設定を追加。

**4-3. docker-compose.yml更新**

環境変数`SMTP_*`を追加。

**4-4. README.md更新**

SMTP設定手順、Docker Secrets使用例を追加。

### Step 5: 統合テスト

**5-1. Example Appでの動作確認**

```bash
# Auth Stack起動
cd auth-stack
docker-compose up -d

# Example App起動
cd ../examples/fastapi-app
pip install -r requirements.txt
uvicorn main:app --reload

# Rate Limiting動作確認
for i in {1..10}; do curl http://localhost:8000/protected; done
# → 6回目以降で429エラー
```

**5-2. Keycloak設定確認**

1. http://localhost:8080/admin にアクセス
2. Realm設定 → SMTP設定が反映されているか確認
3. Required Actions → VERIFY_EMAIL, CONFIGURE_TOTP が有効か確認
4. テストメール送信

## TDD実装計画

### Cycle 1: InMemoryRateLimitStore

**[Red]**: `test_check_and_increment_under_limit` 失敗
**[Green]**: `check_and_increment`実装（シンプルな辞書）
**[Refactor]**: TTLCache導入、スレッドセーフ化

**[Red]**: `test_check_and_increment_over_limit` 失敗
**[Green]**: 制限値チェック追加
**[Refactor]**: エッジケース処理

**[Red]**: `test_cache_warning_at_90_percent` 失敗
**[Green]**: 90%閾値で警告ログ
**[Refactor]**: ログ重複防止（1分間隔）

### Cycle 2: RateLimitMiddleware

**[Red]**: `test_rate_limit_normal_request` 失敗（X-RateLimit-*ヘッダー検証）
**[Green]**: Middleware基本実装
**[Refactor]**: コード整理

**[Red]**: `test_rate_limit_exceeded_returns_429` 失敗
**[Green]**: 429レスポンス実装
**[Refactor]**: Retry-Afterヘッダー追加

**[Red]**: `test_trusted_proxy_forwarded_ip` 失敗
**[Green]**: X-Forwarded-For検証実装
**[Refactor]**: `ipaddress`モジュール活用、エラーハンドリング

**[Red]**: `test_endpoint_specific_limits` 失敗
**[Green]**: エンドポイント別制限実装
**[Refactor]**: 設定の柔軟性向上

### Cycle 3: 統合テスト

**[Red]**: Example Appで429エラーが出ない
**[Green]**: `setup_auth`でMiddleware追加
**[Refactor]**: Middleware順序の最適化

## 議論のポイント

### 論点1: Middlewareの順序

**Engineer**: Rate Limitingは最初に適用すべきか、JWTAuthの後か？

**Security**: 最初に適用すべき。認証前にブルートフォース攻撃を防ぐのが目的。

**Architect**: 同意。ただし、`/auth/health`は除外する（監視用）。

**決定**: Rate Limitingを最初に追加。`/auth/health`はスキップ。

### 論点2: キャッシュmaxsizeのデフォルト値

**DB**: 10,000は小規模システム向け。大規模では不足する可能性。

**Engineer**: 環境変数で設定可能にする？

**Architect**: Phase 2aでは固定値（10,000）で良い。Phase 3でRedis移行時に再検討。

**決定**: maxsize=10,000、将来的に設定可能化を検討。

### 論点3: テストでの時間制御

**Engineer**: TTLCacheのテストで時間待機（`sleep`）が必要？

**Architect**: 不要。`clear_cache`メソッドでキャッシュクリアしてテスト。

**決定**: 時間待機なし、`clear_cache`でテスト効率化。

## 次のアクション

- [x] 実装計画確定
- [ ] Step 1: Rate Limiting基盤実装（TDD）
- [ ] Step 2: Middleware実装（TDD）
- [ ] Step 3: 設定拡張
- [ ] Step 4: Auth Stack設定更新
- [ ] Step 5: 統合テスト
- [ ] `/review` で実装レビュー
- [ ] `/push` でコミット
