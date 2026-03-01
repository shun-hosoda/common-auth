# ADR-007: Rate Limiting方式の選定

## ステータス

承認

## コンテキスト

Phase 2でIPベースのRate Limiting機能を実装する必要がある（FR-013）。この機能はブルートフォース攻撃やクレデンシャルスタッフィング攻撃からシステムを保護するために不可欠である。

Rate Limitingの実装には複数のアルゴリズムとストレージ方式が存在し、それぞれにトレードオフがある。

### 要件
- ログインエンドポイント: 厳しい制限（5 req/min）
- その他API: 緩やかな制限（60 req/min）
- エンドポイント別に異なる制限値を設定可能
- 実クライアントIPの取得（X-Forwarded-For対応）
- 429 Too Many Requestsレスポンス + Retry-Afterヘッダー
- Phase 1では単一インスタンス前提、将来的に水平スケール対応

## 決定

**Token Bucket方式**を採用し、**Phase 2aではメモリキャッシュ（`cachetools.TTLCache`）**で実装する。

### アルゴリズム: Token Bucket

各クライアントIPに「トークンバケット」を割り当て、以下のルールで動作:
1. バケットに初期トークン数を設定（例: 60）
2. リクエストごとに1トークン消費
3. 一定時間（1分）でトークンが補充される
4. トークンが0の場合、リクエストを拒否（429）

### ストレージ: メモリキャッシュ（Phase 2a）

```python
from cachetools import TTLCache

class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self, maxsize: int = 10000):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=60)
        self._lock = threading.Lock()
```

**将来の拡張性**: `RateLimitStore`抽象クラスを定義し、Redis実装への切り替えを容易にする。

```python
class RateLimitStore(ABC):
    @abstractmethod
    def check_and_increment(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        pass
```

## 選択肢

### 選択肢A: Token Bucket（採用）
- **メリット**: 
  - 実装がシンプル
  - メモリ効率が良い（状態はカウンターのみ）
  - バースト対応（短時間の急激なリクエストを吸収可能）
  - トークン残数を容易に計算可能（X-RateLimit-Remainingヘッダー）
- **デメリット**: 
  - 厳密な時間窓管理が難しい（Sliding Windowより精度が低い）

### 選択肢B: Sliding Window
- **メリット**: 
  - より正確なレート制限（任意の時間窓で正確にカウント）
  - 時間窓の境界問題がない
- **デメリット**: 
  - 実装が複雑（各リクエストのタイムスタンプを保持）
  - メモリ消費が大きい（リクエスト履歴を保存）
  - 計算コストが高い（時間窓内のリクエスト数を毎回計算）

### 選択肢C: Fixed Window
- **メリット**: 
  - 実装が最もシンプル
  - メモリ効率が最高（カウンターと窓の開始時刻のみ）
- **デメリット**: 
  - 時間窓の境界でバースト脆弱性（窓の終わりと始まりで2倍のリクエストが可能）
  - 制限の精度が低い

### 選択肢D: Leaky Bucket
- **メリット**: 
  - トラフィック平滑化（一定レートでリクエストを処理）
  - 実装がシンプル
- **デメリット**: 
  - キューイングが必要（レイテンシ増加）
  - API Rate Limitingには不向き（リクエスト即座に拒否が望ましい）

## ストレージ選択肢

### 選択肢A: メモリキャッシュ（Phase 2a採用）
- **メリット**: 
  - 実装がシンプル、外部依存なし
  - 低レイテンシ
  - Docker単一コンテナで動作（ポータビリティ重視）
- **デメリット**: 
  - 水平スケール不可（複数インスタンス間で状態共有できない）
  - 再起動で状態リセット

### 選択肢B: Redis（Phase 3検討）
- **メリット**: 
  - 水平スケール対応（複数インスタンス間で状態共有）
  - 永続化オプション
  - Atomic操作（INCR, EXPIRE）
- **デメリット**: 
  - 外部依存（Redisコンテナが必要、ポータビリティ低下）
  - 運用複雑化

### 選択肢C: PostgreSQL
- **メリット**: 
  - 既存のDBを活用（新規コンポーネント不要）
  - 永続化
- **デメリット**: 
  - レイテンシが高い（Rate LimitingにDB接続は重い）
  - DBへの負荷増加
  - Atomic操作が複雑（Row Lock必要）

## 結果

### 実装への影響

1. **新規ファイル**:
   - `packages/backend-sdk/src/common_auth/middleware/rate_limit.py`
   - `packages/backend-sdk/tests/unit/test_rate_limit.py`

2. **設定追加** (`config.py`):
   ```python
   rate_limit_enabled: bool = True
   rate_limit_default_requests: int = 60
   rate_limit_login_requests: int = 5
   rate_limit_trusted_proxies: list[str] = []
   ```

3. **setup関数拡張**:
   ```python
   def setup_auth(app: FastAPI, config: AuthConfig):
       if config.rate_limit_enabled:
           app.add_middleware(RateLimitMiddleware, config=config)
       # ... existing middleware ...
   ```

### トレードオフ

- **単一インスタンス制限**: Phase 2aではメモリキャッシュを使用するため、水平スケール時にRate Limitingが各インスタンスで独立動作する。例えば、2インスタンス構成で5 req/minの制限がある場合、実質的に10 req/minまで許容される。
  - **対策**: Phase 3でRedis対応を実装する。`RateLimitStore`抽象化により、コードの大部分は変更不要。

- **メモリ使用量**: TTLCacheで最大10,000クライアントを保持（約500KB程度）。大規模システムではmaxsizeを調整可能。
  - **推奨値**: 小規模システム（<1,000ユーザー）: maxsize=10,000、大規模システム（>10,000ユーザー）: maxsize=100,000以上
  - **実測メモリ**: Pythonオブジェクトオーバーヘッド含め、1エントリ約100-150バイト。maxsize=10,000で約1.5MB、maxsize=100,000で約15MB

- **キャッシュ満杯時の挙動**: TTLCacheはLRU (Least Recently Used) evictionを使用。キャッシュが満杯になると、最も古いエントリが削除される。
  - **影響**: 頻繁にアクセスするIPは保護されるが、散発的な攻撃者（多数のIPを使う攻撃）は制限を回避できる可能性がある
  - **対策**: キャッシュ満杯時にWARNINGログを出力し、監視アラートで検知。Phase 3でRedis移行時に根本解決

- **再起動時の状態**: アプリ再起動でRate Limiting状態がリセットされる。これは攻撃者が再起動を誘発することで制限を回避できる可能性があるが、Phase 1の要件では許容範囲。

### 実装詳細ガイド

#### X-Forwarded-For検証の実装

```python
from ipaddress import ip_address, ip_network, AddressValueError
import logging

logger = logging.getLogger(__name__)

def _get_client_ip(self, request: Request) -> str:
    """
    実クライアントIPを取得。X-Forwarded-Forを考慮。
    
    Args:
        request: FastAPI Request
    
    Returns:
        クライアントIP文字列
    """
    # X-Forwarded-For検証
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and self._is_trusted_proxy(request.client.host):
        # 最初のIPを返す（クライアント側）
        return forwarded.split(",")[0].strip()
    return request.client.host

def _is_trusted_proxy(self, ip: str) -> bool:
    """
    プロキシが信頼リストに含まれるか確認。
    
    Args:
        ip: チェック対象のIPアドレス
    
    Returns:
        信頼できるプロキシの場合True
    
    Example:
        config.rate_limit_trusted_proxies = ["10.0.0.0/8", "172.16.0.0/12"]
    """
    if not self.config.rate_limit_trusted_proxies:
        # 信頼プロキシ未設定の場合、X-Forwarded-Forを信用しない
        return False
    
    try:
        client_ip = ip_address(ip)
        for cidr in self.config.rate_limit_trusted_proxies:
            try:
                if client_ip in ip_network(cidr):
                    return True
            except (ValueError, AddressValueError):
                logger.warning(f"Invalid CIDR range in trusted_proxies: {cidr}")
                continue
    except (ValueError, AddressValueError):
        logger.warning(f"Invalid IP address: {ip}")
        return False
    
    return False
```

**設定例**:
```python
# AWS ALB背後
rate_limit_trusted_proxies = ["10.0.0.0/8"]

# Cloudflare背後
rate_limit_trusted_proxies = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
    # ... Cloudflare IP ranges
]

# 複数プロキシ
rate_limit_trusted_proxies = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
```

#### キャッシュ満杯検知のログ実装

```python
class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self, maxsize: int = 10000):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=60)
        self._lock = threading.Lock()
        self._last_warning = 0  # 最後の警告時刻
    
    def check_and_increment(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        with self._lock:
            # キャッシュ使用率チェック
            if len(self._cache) >= self._cache.maxsize * 0.9:
                # 90%以上で警告（1分に1回まで）
                import time
                now = time.time()
                if now - self._last_warning > 60:
                    logger.warning(
                        f"Rate limit cache usage high: {len(self._cache)}/{self._cache.maxsize}. "
                        "Consider increasing maxsize or migrating to Redis."
                    )
                    self._last_warning = now
            
            current = self._cache.get(key, 0)
            if current >= limit:
                return (False, 0)
            self._cache[key] = current + 1
            remaining = limit - (current + 1)
            return (True, remaining)
```

### セキュリティ考慮事項

- **X-Forwarded-For検証**: 信頼プロキシのCIDR範囲を設定し、範囲外のプロキシからの`X-Forwarded-For`は無視する。
- **分散DoS対応**: 多数の異なるIPからの攻撃には効果が限定的。CDNレベルのDDoS対策が別途必要。
- **認証済みエンドポイント**: 将来的にユーザーID単位のRate Limitingも検討（1ユーザーが複数IPから攻撃する場合への対策）。

### Phase 3での拡張計画

#### ユーザーID単位Rate Limiting

認証済みエンドポイントに対して、ユーザーID単位のRate Limitingを追加実装予定。

**ユースケース**:
- 1ユーザーが複数IP（プロキシ、VPN切り替え）から大量リクエストを送る攻撃
- API abuse（正規ユーザーによる過剰利用）

**実装方針**:
```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # IP単位チェック（既存）
        ip_key = f"ratelimit:ip:{client_ip}:{path}"
        ip_allowed, _ = self.store.check_and_increment(ip_key, ip_limit, 60)
        
        if not ip_allowed:
            return JSONResponse(status_code=429, ...)
        
        # 認証済みの場合、ユーザーID単位でもチェック
        if hasattr(request.state, 'user') and request.state.user:
            user_id = request.state.user.sub
            user_key = f"ratelimit:user:{user_id}:{path}"
            user_allowed, _ = self.store.check_and_increment(user_key, user_limit, 60)
            
            if not user_allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": "user_rate_limit_exceeded", ...}
                )
        
        return await call_next(request)
```

**設定追加**:
```python
rate_limit_user_requests: int = 120  # 認証済みユーザーはIP制限の2倍
```

## 参考

- [Token Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- [Leaky Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Leaky_bucket)
- [Scaling your API with rate limiters - Stripe Engineering](https://stripe.com/blog/rate-limiters)
- [Python cachetools library](https://cachetools.readthedocs.io/)
- [RFC 6585 - Additional HTTP Status Codes (429 Too Many Requests)](https://datatracker.ietf.org/doc/html/rfc6585#section-4)
