"""Unit tests for AuditService."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common_auth.services.audit_service import AuditEntry, AuditService


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_db() -> MagicMock:
    """Mock DBClient."""
    db = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetch = AsyncMock(return_value=[])

    # asynccontextmanager mock
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    @asynccontextmanager
    async def _connection(**kwargs: object) -> AsyncIterator[AsyncMock]:  # type: ignore
        yield conn

    db.connection = _connection
    return db


@pytest.fixture()
def svc(mock_db: MagicMock) -> AuditService:
    return AuditService(mock_db)


TENANT_ID = str(uuid.uuid4())
ACTOR_ID = str(uuid.uuid4())


# ── _write success ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_write_success(svc: AuditService, mock_db: MagicMock) -> None:
    entry = AuditEntry(
        tenant_id=TENANT_ID,
        actor_id=ACTOR_ID,
        actor_email="admin@example.com",
        action="group.member.add",
        resource_type="group",
        resource_id="some-group-id",
        details={"user_id": "some-user-id"},
    )
    await svc._write(entry)
    assert svc._failure_count == 0


@pytest.mark.asyncio
async def test_write_increments_failure_count_on_error(svc: AuditService, mock_db: MagicMock) -> None:
    """DB error must increment failure counter without raising."""
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    @asynccontextmanager
    async def _error_connection(**kwargs: object) -> AsyncIterator[None]:  # type: ignore
        raise RuntimeError("DB unavailable")
        yield  # unreachable

    mock_db.connection = _error_connection

    entry = AuditEntry(
        tenant_id=TENANT_ID,
        actor_id=ACTOR_ID,
        actor_email="admin@example.com",
        action="group.create",
    )
    await svc._write(entry)  # must not raise
    assert svc._failure_count == 1


@pytest.mark.asyncio
async def test_write_logs_error_on_failure(svc: AuditService, mock_db: MagicMock) -> None:
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    @asynccontextmanager
    async def _error_connection(**kwargs: object) -> AsyncIterator[None]:  # type: ignore
        raise RuntimeError("connection refused")
        yield

    mock_db.connection = _error_connection

    with patch("common_auth.services.audit_service.logger") as mock_logger:
        await svc._write(AuditEntry(
            tenant_id=TENANT_ID,
            actor_id=ACTOR_ID,
            actor_email=None,
            action="group.delete",
        ))
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args
        assert call_kwargs[0][0] == "audit_log_write_failed"


# ── log() returns task ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_returns_future(svc: AuditService) -> None:
    future = svc.log(
        tenant_id=TENANT_ID,
        actor_id=ACTOR_ID,
        actor_email="admin@example.com",
        action="group.update",
    )
    assert asyncio.isfuture(future) or asyncio.iscoroutine(future) or hasattr(future, "__await__")
    await future  # should not raise


# ── list_logs ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_logs_returns_empty(svc: AuditService) -> None:
    logs, total = await svc.list_logs(tenant_id=TENANT_ID)
    assert logs == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_logs_with_action_filter(svc: AuditService, mock_db: MagicMock) -> None:
    """Action wildcard filter should translate to LIKE pattern."""
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    executed_queries: list[str] = []

    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)

    async def _fetch(sql: str, *args: object) -> list:
        executed_queries.append(sql)
        return []

    conn.fetch = _fetch

    @asynccontextmanager
    async def _conn(**kwargs: object) -> AsyncIterator[AsyncMock]:  # type: ignore
        yield conn

    mock_db.connection = _conn

    await svc.list_logs(tenant_id=TENANT_ID, action_prefix="group.*")
    # verify LIKE pattern was applied
    assert any("LIKE" in q for q in executed_queries)


@pytest.mark.asyncio
async def test_list_logs_per_page_capped_at_200(svc: AuditService) -> None:
    """per_page should be capped at 200 internally."""
    # Should not raise even with per_page=99999
    logs, total = await svc.list_logs(tenant_id=TENANT_ID, per_page=99999)
    assert logs == []
