"""Rate limiting middleware using fixed-window counter algorithm."""

import logging
import threading
import time
from abc import ABC, abstractmethod
from ipaddress import AddressValueError, ip_address, ip_network

from cachetools import TTLCache
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitStore(ABC):
    """Abstract base class for rate limiting state storage.
    
    Implement this interface to provide custom storage backends
    (e.g., Redis for horizontal scaling).
    """

    @abstractmethod
    def check_and_increment(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int]:
        """Check rate limit and increment counter.

        Args:
            key: Client identifier (typically IP + path)
            limit: Maximum requests allowed in the window
            window: Time window in seconds

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        ...

    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset the counter for a given key."""
        ...


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store using TTLCache (single-instance only).

    Uses cachetools.TTLCache for automatic expiration. Thread-safe via
    threading.Lock. Not suitable for horizontally scaled deployments;
    use a Redis-backed store instead for multi-instance setups.
    """

    def __init__(self, maxsize: int = 10_000, ttl: int = 60) -> None:
        self._cache: TTLCache[str, int] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()
        self._last_capacity_warning: float = 0

    def check_and_increment(
        self, key: str, limit: int, window: int  # noqa: ARG002 — window handled by TTL
    ) -> tuple[bool, int]:
        with self._lock:
            self._warn_if_near_capacity()

            current: int = self._cache.get(key, 0)
            if current >= limit:
                return (False, 0)

            self._cache[key] = current + 1
            remaining = limit - (current + 1)
            return (True, remaining)

    def reset(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def _warn_if_near_capacity(self) -> None:
        usage = len(self._cache)
        threshold = int(self._cache.maxsize * 0.9)
        if usage >= threshold:
            now = time.monotonic()
            if now - self._last_capacity_warning > 60:
                logger.warning(
                    "Rate limit cache at %d/%d (%.0f%%). "
                    "Consider increasing maxsize or migrating to Redis.",
                    usage,
                    self._cache.maxsize,
                    usage / self._cache.maxsize * 100,
                )
                self._last_capacity_warning = now

    @property
    def size(self) -> int:
        """Current number of tracked clients."""
        return len(self._cache)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window counter rate limiting middleware.

    Limits requests per client IP, with configurable per-endpoint limits.
    Adds standard rate-limit headers to every response.
    """

    SKIP_PATHS: frozenset[str] = frozenset({"/auth/health", "/docs", "/openapi.json"})

    def __init__(self, app, *, config, store: RateLimitStore | None = None) -> None:
        super().__init__(app)
        self.config = config
        self.store: RateLimitStore = store or InMemoryRateLimitStore()
        self._trusted_networks = self._parse_trusted_proxies(
            getattr(config, "rate_limit_trusted_proxies", [])
        )

    async def dispatch(self, request: Request, call_next):
        if not getattr(self.config, "rate_limit_enabled", True):
            return await call_next(request)

        path = request.url.path
        if path in self.SKIP_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        limit = self._get_limit_for_path(path)
        key = f"rl:{client_ip}:{path}"

        allowed, remaining = self.store.check_and_increment(key, limit, 60)

        if not allowed:
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "too_many_requests",
                    "message": "Rate limit exceeded. Please retry later.",
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _get_limit_for_path(self, path: str) -> int:
        login_limit = getattr(self.config, "rate_limit_login_requests", 5)
        default_limit = getattr(self.config, "rate_limit_default_requests", 60)

        if path in {"/auth/login", "/auth/logout"}:
            return login_limit
        return default_limit

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        client_host = request.client.host if request.client else "unknown"

        if forwarded and self._is_trusted_proxy(client_host):
            real_ip = forwarded.split(",")[0].strip()
            logger.debug("Trusted proxy %s, using forwarded IP %s", client_host, real_ip)
            return real_ip

        return client_host

    def _is_trusted_proxy(self, ip: str) -> bool:
        if not self._trusted_networks:
            return False
        try:
            addr = ip_address(ip)
            return any(addr in net for net in self._trusted_networks)
        except (ValueError, AddressValueError):
            logger.warning("Invalid IP address for proxy check: %s", ip)
            return False

    @staticmethod
    def _parse_trusted_proxies(cidrs: list[str]) -> list:
        networks = []
        for cidr in cidrs:
            try:
                networks.append(ip_network(cidr, strict=False))
            except (ValueError, AddressValueError):
                logger.warning("Invalid CIDR in rate_limit_trusted_proxies: %s", cidr)
        return networks
