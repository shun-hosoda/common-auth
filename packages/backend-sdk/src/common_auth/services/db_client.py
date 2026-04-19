"""Async PostgreSQL connection pool wrapper with RLS tenant isolation.

Usage:
    # On app startup
    db = await DBClient.create(dsn)
    app.state.db = db

    # In service layer
    async with db.connection(tenant_id=user.tenant_id) as conn:
        rows = await conn.fetch("SELECT * FROM tenant_groups WHERE is_active")

    # On app shutdown
    await db.close()
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import asyncpg


class DBClient:
    """asyncpg connection pool with automatic RLS tenant isolation.

    Each call to ``connection()`` acquires a connection from the pool and
    immediately executes ``SELECT set_config('app.current_tenant_id', $1, true)``
    so that PostgreSQL RLS policies apply to the calling tenant only.

    Pass ``skip_rls=True`` for super_admin cross-tenant operations (the
    ``set_config`` call is skipped entirely).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    async def create(
        cls,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
        command_timeout: float = 30.0,
    ) -> "DBClient":
        """Create and return a connected DBClient instance."""
        pool = await asyncpg.create_pool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
        return cls(pool)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Gracefully terminate the connection pool."""
        await self._pool.close()

    # ── Connection context manager ────────────────────────────────────────────

    @asynccontextmanager
    async def connection(
        self,
        *,
        tenant_id: Optional[str],
        skip_rls: bool = False,
    ) -> AsyncIterator[asyncpg.Connection]:
        """Yield an asyncpg connection with RLS tenant isolation applied.

        Args:
            tenant_id: The tenant identifier to scope queries.
                       Must be a non-empty string unless skip_rls=True.
            skip_rls:  When True, skip SET LOCAL (for super_admin use).

        Raises:
            ValueError: if tenant_id is empty/None and skip_rls is False.
        """
        if not skip_rls:
            if not tenant_id:
                raise ValueError(
                    "tenant_id must be a non-empty string. "
                    "Pass skip_rls=True for super_admin cross-tenant access."
                )

        async with self._pool.acquire() as conn:
            if not skip_rls and tenant_id:
                await conn.execute(
                    "SELECT set_config('app.current_tenant_id', $1, true)",
                    tenant_id,
                )
            yield conn
