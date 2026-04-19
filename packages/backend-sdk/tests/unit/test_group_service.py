"""Unit tests for GroupService — tenant_groups CRUD and membership management.

All DB calls are mocked so no real database is required.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from common_auth.services.group_service import GroupService
from common_auth.models.group import GroupCreate, GroupUpdate


# ── Fixtures ──────────────────────────────────────────────────────────────────

TENANT_ID = "acme-corp"
GROUP_ID = uuid.uuid4()
USER_ID = uuid.uuid4()

NOW = datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)

SAMPLE_GROUP_ROW = {
    "id": GROUP_ID,
    "tenant_id": TENANT_ID,
    "name": "Engineering",
    "description": "Engineering team",
    "parent_group_id": None,
    "is_active": True,
    "sort_order": 0,
    "member_count": 3,
    "created_at": NOW,
    "updated_at": NOW,
}


def _mock_conn(fetch_result=None, fetchrow_result=None, execute_result=None):
    """Return a mock asyncpg connection."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetchval = AsyncMock(return_value=execute_result)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _mock_db(conn):
    """Return a mock DBClient whose connection() context manager yields conn."""
    db = MagicMock()
    db.connection = MagicMock()
    db.connection.return_value.__aenter__ = AsyncMock(return_value=conn)
    db.connection.return_value.__aexit__ = AsyncMock(return_value=False)
    return db


# ── list_groups ───────────────────────────────────────────────────────────────


class TestListGroups:
    async def test_returns_list_and_total(self):
        conn = _mock_conn(fetch_result=[SAMPLE_GROUP_ROW])
        conn.fetchval = AsyncMock(return_value=1)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.list_groups(tenant_id=TENANT_ID, page=1, page_size=20)

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "Engineering"

    async def test_search_queries_are_applied(self):
        conn = _mock_conn(fetch_result=[])
        conn.fetchval = AsyncMock(return_value=0)
        db = _mock_db(conn)

        svc = GroupService(db)
        await svc.list_groups(tenant_id=TENANT_ID, page=1, page_size=20, search="eng")

        # fetch was called — verify search keyword was passed
        fetch_call = conn.fetch.call_args
        assert "eng" in str(fetch_call)


# ── get_group ─────────────────────────────────────────────────────────────────


class TestGetGroup:
    async def test_returns_group_when_found(self):
        conn = _mock_conn(fetchrow_result=SAMPLE_GROUP_ROW)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.get_group(tenant_id=TENANT_ID, group_id=GROUP_ID)

        assert result is not None
        assert result["id"] == GROUP_ID

    async def test_returns_none_when_not_found(self):
        conn = _mock_conn(fetchrow_result=None)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.get_group(tenant_id=TENANT_ID, group_id=GROUP_ID)

        assert result is None


# ── create_group ──────────────────────────────────────────────────────────────


class TestCreateGroup:
    async def test_creates_and_returns_group(self):
        conn = _mock_conn(fetchrow_result=SAMPLE_GROUP_ROW)
        db = _mock_db(conn)

        svc = GroupService(db)
        payload = GroupCreate(name="Engineering", description="Engineering team")
        result = await svc.create_group(tenant_id=TENANT_ID, payload=payload)

        conn.fetchrow.assert_called_once()
        assert result["name"] == "Engineering"

    async def test_tenant_id_injected_in_query(self):
        conn = _mock_conn(fetchrow_result=SAMPLE_GROUP_ROW)
        db = _mock_db(conn)

        svc = GroupService(db)
        payload = GroupCreate(name="Test")
        await svc.create_group(tenant_id=TENANT_ID, payload=payload)

        # Connection was acquired with correct tenant_id
        db.connection.assert_called_with(tenant_id=TENANT_ID)


# ── update_group ──────────────────────────────────────────────────────────────


class TestUpdateGroup:
    async def test_update_returns_updated_group(self):
        updated = {**SAMPLE_GROUP_ROW, "name": "Platform Engineering"}
        conn = _mock_conn(fetchrow_result=updated)
        db = _mock_db(conn)

        svc = GroupService(db)
        payload = GroupUpdate(name="Platform Engineering")
        result = await svc.update_group(
            tenant_id=TENANT_ID, group_id=GROUP_ID, payload=payload
        )

        assert result["name"] == "Platform Engineering"

    async def test_update_nonexistent_returns_none(self):
        conn = _mock_conn(fetchrow_result=None)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.update_group(
            tenant_id=TENANT_ID, group_id=GROUP_ID, payload=GroupUpdate(name="X")
        )

        assert result is None


# ── delete_group (logical) ────────────────────────────────────────────────────


class TestDeleteGroup:
    async def test_delete_returns_true_when_found(self):
        conn = _mock_conn()
        conn.fetchval = AsyncMock(return_value=GROUP_ID)  # returns updated id
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.delete_group(tenant_id=TENANT_ID, group_id=GROUP_ID)

        assert result is True

    async def test_delete_returns_false_when_not_found(self):
        conn = _mock_conn()
        conn.fetchval = AsyncMock(return_value=None)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.delete_group(tenant_id=TENANT_ID, group_id=GROUP_ID)

        assert result is False


# ── list_members ──────────────────────────────────────────────────────────────


class TestListMembers:
    async def test_returns_members(self):
        member_row = {
            "user_id": USER_ID,
            "email": "alice@example.com",
            "display_name": "Alice",
            "joined_at": NOW,
        }
        conn = _mock_conn(fetch_result=[member_row])
        conn.fetchval = AsyncMock(return_value=1)
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.list_members(tenant_id=TENANT_ID, group_id=GROUP_ID)

        assert result["total"] == 1
        assert result["items"][0]["email"] == "alice@example.com"


# ── add_members ───────────────────────────────────────────────────────────────


class TestAddMembers:
    async def test_add_members_executes_insert(self):
        conn = _mock_conn()
        db = _mock_db(conn)

        svc = GroupService(db)
        await svc.add_members(
            tenant_id=TENANT_ID,
            group_id=GROUP_ID,
            user_ids=[USER_ID],
            added_by=uuid.uuid4(),
        )

        conn.executemany.assert_called_once()


# ── remove_member ─────────────────────────────────────────────────────────────


class TestRemoveMember:
    async def test_remove_returns_true_when_deleted(self):
        conn = _mock_conn()
        conn.execute = AsyncMock(return_value="DELETE 1")
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.remove_member(
            tenant_id=TENANT_ID, group_id=GROUP_ID, user_id=USER_ID
        )

        assert result is True

    async def test_remove_returns_false_when_not_found(self):
        conn = _mock_conn()
        conn.execute = AsyncMock(return_value="DELETE 0")
        db = _mock_db(conn)

        svc = GroupService(db)
        result = await svc.remove_member(
            tenant_id=TENANT_ID, group_id=GROUP_ID, user_id=USER_ID
        )

        assert result is False
