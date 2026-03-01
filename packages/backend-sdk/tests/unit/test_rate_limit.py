"""Tests for rate limiting middleware."""

from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common_auth.middleware.rate_limit import (
    InMemoryRateLimitStore,
    RateLimitMiddleware,
)


# ═══════════════════════════════════════════════════
#  InMemoryRateLimitStore tests
# ═══════════════════════════════════════════════════

class TestInMemoryRateLimitStore:

    def test_allows_requests_under_limit(self):
        store = InMemoryRateLimitStore(maxsize=100)
        allowed, remaining = store.check_and_increment("ip:1", limit=5, window=60)
        assert allowed is True
        assert remaining == 4

    def test_blocks_requests_over_limit(self):
        store = InMemoryRateLimitStore(maxsize=100)
        for _ in range(5):
            store.check_and_increment("ip:1", limit=5, window=60)

        allowed, remaining = store.check_and_increment("ip:1", limit=5, window=60)
        assert allowed is False
        assert remaining == 0

    def test_remaining_decrements_correctly(self):
        store = InMemoryRateLimitStore(maxsize=100)
        results = []
        for _ in range(5):
            allowed, remaining = store.check_and_increment("ip:1", limit=5, window=60)
            results.append((allowed, remaining))

        assert results == [
            (True, 4),
            (True, 3),
            (True, 2),
            (True, 1),
            (True, 0),
        ]

    def test_different_keys_are_independent(self):
        store = InMemoryRateLimitStore(maxsize=100)
        for _ in range(5):
            store.check_and_increment("ip:A", limit=5, window=60)

        allowed, remaining = store.check_and_increment("ip:B", limit=5, window=60)
        assert allowed is True
        assert remaining == 4

    def test_reset_clears_key(self):
        store = InMemoryRateLimitStore(maxsize=100)
        for _ in range(5):
            store.check_and_increment("ip:1", limit=5, window=60)

        store.reset("ip:1")
        allowed, remaining = store.check_and_increment("ip:1", limit=5, window=60)
        assert allowed is True
        assert remaining == 4

    def test_size_tracks_entries(self):
        store = InMemoryRateLimitStore(maxsize=100)
        assert store.size == 0
        store.check_and_increment("ip:1", limit=5, window=60)
        store.check_and_increment("ip:2", limit=5, window=60)
        assert store.size == 2


# ═══════════════════════════════════════════════════
#  RateLimitMiddleware tests
# ═══════════════════════════════════════════════════

def _make_app(
    *,
    enabled: bool = True,
    default_requests: int = 60,
    login_requests: int = 5,
    trusted_proxies: list[str] | None = None,
    store: InMemoryRateLimitStore | None = None,
) -> FastAPI:
    """Helper to create a FastAPI app with RateLimitMiddleware."""
    config = MagicMock()
    config.rate_limit_enabled = enabled
    config.rate_limit_default_requests = default_requests
    config.rate_limit_login_requests = login_requests
    config.rate_limit_trusted_proxies = trusted_proxies or []

    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        config=config,
        store=store,
    )

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.post("/auth/login")
    async def login_endpoint():
        return {"status": "ok"}

    @app.get("/auth/health")
    async def health_endpoint():
        return {"status": "ok"}

    return app


class TestRateLimitMiddleware:

    def test_normal_request_includes_headers(self):
        app = _make_app(default_requests=10)
        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert response.headers["X-RateLimit-Remaining"] == "9"

    def test_returns_429_when_limit_exceeded(self):
        app = _make_app(default_requests=3)
        client = TestClient(app)

        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        assert response.json()["error"] == "too_many_requests"

    def test_login_has_stricter_limit(self):
        app = _make_app(default_requests=60, login_requests=2)
        client = TestClient(app)

        for _ in range(2):
            response = client.post("/auth/login")
            assert response.status_code == 200

        response = client.post("/auth/login")
        assert response.status_code == 429

    def test_different_endpoints_have_separate_counters(self):
        app = _make_app(default_requests=60, login_requests=2)
        client = TestClient(app)

        for _ in range(2):
            client.post("/auth/login")

        response = client.post("/auth/login")
        assert response.status_code == 429

        response = client.get("/test")
        assert response.status_code == 200

    def test_health_endpoint_is_not_rate_limited(self):
        app = _make_app(default_requests=1)
        client = TestClient(app)

        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429

        for _ in range(10):
            response = client.get("/auth/health")
            assert response.status_code == 200

    def test_disabled_rate_limiting_passes_through(self):
        app = _make_app(enabled=False, default_requests=1)
        client = TestClient(app)

        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200

    def test_x_forwarded_for_with_trusted_proxy(self):
        app = _make_app(
            default_requests=2,
            trusted_proxies=["10.0.0.0/8"],
        )
        client = TestClient(app)

        # testclient sends from 'testclient' which is not a trusted proxy
        # so X-Forwarded-For will be ignored by default
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert response.status_code == 200

    def test_shared_store_across_middleware(self):
        """Verify that injecting a custom store works."""
        store = InMemoryRateLimitStore(maxsize=100)
        app = _make_app(default_requests=2, store=store)
        client = TestClient(app)

        client.get("/test")
        assert store.size >= 1

    def test_remaining_decrements_per_request(self):
        app = _make_app(default_requests=3)
        client = TestClient(app)

        r1 = client.get("/test")
        r2 = client.get("/test")
        r3 = client.get("/test")

        assert r1.headers["X-RateLimit-Remaining"] == "2"
        assert r2.headers["X-RateLimit-Remaining"] == "1"
        assert r3.headers["X-RateLimit-Remaining"] == "0"
