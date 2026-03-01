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

- **再起動時の状態**: アプリ再起動でRate Limiting状態がリセットされる。これは攻撃者が再起動を誘発することで制限を回避できる可能性があるが、Phase 1の要件では許容範囲。

### セキュリティ考慮事項

- **X-Forwarded-For検証**: 信頼プロキシのCIDR範囲を設定し、範囲外のプロキシからの`X-Forwarded-For`は無視する。
- **分散DoS対応**: 多数の異なるIPからの攻撃には効果が限定的。CDNレベルのDDoS対策が別途必要。
- **認証済みエンドポイント**: 将来的にユーザーID単位のRate Limitingも検討（1ユーザーが複数IPから攻撃する場合への対策）。

## 参考

- [Token Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- [Leaky Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Leaky_bucket)
- [Scaling your API with rate limiters - Stripe Engineering](https://stripe.com/blog/rate-limiters)
- [Python cachetools library](https://cachetools.readthedocs.io/)
- [RFC 6585 - Additional HTTP Status Codes (429 Too Many Requests)](https://datatracker.ietf.org/doc/html/rfc6585#section-4)
