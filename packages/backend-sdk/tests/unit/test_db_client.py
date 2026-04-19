"""Unit tests for DBClient 窶・asyncpg connection pool wrapper.

Tests verify:
1. Pool creation and lifecycle
2. RLS tenant isolation via SET LOCAL
3. Tenant ID injection on every acquired connection
4. Error propagation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from common_auth.services.db_client import DBClient


# 笏笏 Fixtures 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


# 笏笏 Tests 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestDBClientCreate:
    """Pool creation / teardown."""

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_create_returns_db_client(self, mock_create_pool):
        mock_pool_inst = AsyncMock()
        mock_create_pool.return_value = mock_pool_inst

        client = await DBClient.create("postgresql://localhost/test")

        assert isinstance(client, DBClient)
        mock_create_pool.assert_called_once()

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_close_terminates_pool(self, mock_create_pool):
        mock_pool_inst = AsyncMock()
        mock_create_pool.return_value = mock_pool_inst
        client = await DBClient.create("postgresql://localhost/test")

        await client.close()

        mock_pool_inst.close.assert_called_once()


class TestDBClientConnection:
    """Connection acquisition and RLS setup."""

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_acquire_sets_local_tenant_id(self, mock_create_pool):
        """SET LOCAL app.current_tenant_id must be called on every connection."""
        conn = AsyncMock()
        pool = MagicMock()
        pool.close = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool.acquire.return_value = cm
        mock_create_pool.return_value = pool

        client = await DBClient.create("postgresql://localhost/test")

        async with client.connection(tenant_id="acme-corp") as c:
            assert c is conn

        conn.execute.assert_any_call(
            "SELECT set_config('app.current_tenant_id', $1, true)", "acme-corp"
        )

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_acquire_without_tenant_id_raises(self, mock_create_pool):
        """Acquiring a connection without tenant_id must raise ValueError."""
        mock_create_pool.return_value = AsyncMock()
        client = await DBClient.create("postgresql://localhost/test")

        with pytest.raises(ValueError, match="tenant_id"):
            async with client.connection(tenant_id=""):
                pass

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_acquire_none_tenant_id_raises(self, mock_create_pool):
        mock_create_pool.return_value = AsyncMock()
        client = await DBClient.create("postgresql://localhost/test")

        with pytest.raises(ValueError, match="tenant_id"):
            async with client.connection(tenant_id=None):  # type: ignore
                pass

    @patch("common_auth.services.db_client.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_super_admin_bypass_skips_rls(self, mock_create_pool):
        """super_admin=True should skip SET LOCAL (allow cross-tenant access)."""
        conn = AsyncMock()
        pool = MagicMock()
        pool.close = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool.acquire.return_value = cm
        mock_create_pool.return_value = pool

        client = await DBClient.create("postgresql://localhost/test")

        async with client.connection(tenant_id="__super_admin__", skip_rls=True) as c:
            assert c is conn

        # SET LOCAL should NOT have been called
        for c in conn.execute.call_args_list:
            assert "set_config" not in str(c)

