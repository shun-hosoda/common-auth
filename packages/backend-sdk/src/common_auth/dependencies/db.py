"""Database dependencies for FastAPI dependency injection.

Provides FastAPI ``Depends``-compatible functions to acquire database
connections from ``app.state.db_pool``.

Design note (M-2, S-6):
    Public invitation endpoints (validate / accept) run without an
    authenticated user, so ``app.current_tenant_id`` is never set and the
    Row-Level Security (RLS) policy on ``invitation_tokens`` would block
    all queries.

    ``get_db_conn_bypass_rls`` acquires a connection and disables RLS for
    the duration of the transaction by executing
    ``SET LOCAL row_security = off``.  This requires the DB role to have
    the ``BYPASSRLS`` privilege or be a superuser.  In the Docker-compose
    dev environment the ``postgres`` superuser satisfies this requirement.
    For production deployments, create a dedicated DB role with
    ``BYPASSRLS`` and use it exclusively for the invitation service.
"""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, HTTPException, Request, status


async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Return ``app.state.db_pool``.

    Raises:
        HTTPException 503: if the pool is not configured
                          (``APP_DATABASE_URL`` not set).
    """
    pool: asyncpg.Pool | None = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured (APP_DATABASE_URL missing)",
        )
    return pool


async def get_db_conn(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> AsyncIterator[asyncpg.Connection]:
    """Yield a single connection from the pool (with active RLS).

    Usage::

        @router.get("/items")
        async def list_items(conn: asyncpg.Connection = Depends(get_db_conn)):
            ...
    """
    async with pool.acquire() as conn:
        yield conn


async def get_db_conn_bypass_rls(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> AsyncIterator[asyncpg.Connection]:
    """Yield a connection with Row-Level Security disabled.

    Used exclusively by Public invitation endpoints that run without a
    ``app.current_tenant_id`` session variable.  The connection executes
    ``SET LOCAL row_security = off`` inside a transaction so the setting
    is automatically reverted when the transaction ends.

    Security consideration:
        This function is intentionally narrow in scope.  Do NOT use it for
        authenticated multi-tenant endpoints — always use ``get_db_conn``
        there so RLS remains the last line of defence.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL row_security = off")
            yield conn
