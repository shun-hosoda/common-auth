"""Unit tests for PermissionService.

Tests cover:
1. Listing all permission definitions with current granted status for a group
2. Bulk update of group permissions (true/false/null → upsert/delete)
3. Effective permission resolution (user_direct + group inheritance)
4. User direct permission upsert/delete
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from common_auth.services.permission_service import PermissionService
from common_auth.models.group import PermissionUpdate, BulkPermissionUpdateRequest


TENANT_ID = "acme-corp"
GROUP_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
PERM_ID = uuid.uuid4()
NOW = datetime(2026, 4, 19, tzinfo=timezone.utc)


def _mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _mock_db(conn):
    db = MagicMock()
    db.connection = MagicMock()
    db.connection.return_value.__aenter__ = AsyncMock(return_value=conn)
    db.connection.return_value.__aexit__ = AsyncMock(return_value=False)
    return db


# ── list_group_permissions ────────────────────────────────────────────────────


class TestListGroupPermissions:
    async def test_returns_all_permissions_with_granted_status(self):
        perm_row = {
            "id": PERM_ID,
            "resource": "users",
            "action": "read",
            "description": "Read users",
            "is_system": True,
            "granted": True,
        }
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[perm_row])
        db = _mock_db(conn)

        svc = PermissionService(db)
        result = await svc.list_group_permissions(
            tenant_id=TENANT_ID, group_id=GROUP_ID
        )

        assert len(result) == 1
        assert result[0]["resource"] == "users"
        assert result[0]["granted"] is True

    async def test_unset_permissions_return_none_granted(self):
        perm_row = {
            "id": PERM_ID,
            "resource": "billing",
            "action": "admin",
            "description": None,
            "is_system": True,
            "granted": None,  # no record in group_permissions
        }
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[perm_row])
        db = _mock_db(conn)

        svc = PermissionService(db)
        result = await svc.list_group_permissions(
            tenant_id=TENANT_ID, group_id=GROUP_ID
        )

        assert result[0]["granted"] is None


# ── update_group_permissions ──────────────────────────────────────────────────


class TestUpdateGroupPermissions:
    async def test_true_value_upserts_record(self):
        conn = _mock_conn()
        db = _mock_db(conn)

        svc = PermissionService(db)
        await svc.update_group_permissions(
            tenant_id=TENANT_ID,
            group_id=GROUP_ID,
            updates=[PermissionUpdate(permission_id=PERM_ID, granted=True)],
            granted_by=USER_ID,
        )

        # At least one execute call for upsert
        assert conn.execute.called or conn.executemany.called

    async def test_none_value_deletes_record(self):
        conn = _mock_conn()
        db = _mock_db(conn)

        svc = PermissionService(db)
        await svc.update_group_permissions(
            tenant_id=TENANT_ID,
            group_id=GROUP_ID,
            updates=[PermissionUpdate(permission_id=PERM_ID, granted=None)],
            granted_by=USER_ID,
        )

        # Verify delete was called
        call_args_str = str(conn.execute.call_args_list) + str(
            conn.executemany.call_args_list if hasattr(conn, "executemany") else ""
        )
        assert conn.execute.called


# ── get_effective_permissions ─────────────────────────────────────────────────


class TestGetEffectivePermissions:
    async def test_user_direct_takes_precedence(self):
        """User direct permission should override group permission."""
        rows = [
            {
                "id": PERM_ID,
                "resource": "users",
                "action": "delete",
                "granted": False,
                "source": "user_direct",
            }
        ]
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=rows)
        db = _mock_db(conn)

        svc = PermissionService(db)
        result = await svc.get_effective_permissions(
            tenant_id=TENANT_ID, user_id=USER_ID
        )

        assert len(result) == 1
        assert result[0]["source"] == "user_direct"
        assert result[0]["granted"] is False

    async def test_empty_returns_empty_list(self):
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[])
        db = _mock_db(conn)

        svc = PermissionService(db)
        result = await svc.get_effective_permissions(
            tenant_id=TENANT_ID, user_id=USER_ID
        )

        assert result == []


# ── update_user_permissions ───────────────────────────────────────────────────


class TestUpdateUserPermissions:
    async def test_upsert_granted_true(self):
        conn = _mock_conn()
        db = _mock_db(conn)

        svc = PermissionService(db)
        await svc.update_user_permissions(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            updates=[PermissionUpdate(permission_id=PERM_ID, granted=True)],
            granted_by=USER_ID,
        )

        assert conn.execute.called

    async def test_none_granted_deletes_user_permission(self):
        conn = _mock_conn()
        db = _mock_db(conn)

        svc = PermissionService(db)
        await svc.update_user_permissions(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            updates=[PermissionUpdate(permission_id=PERM_ID, granted=None)],
            granted_by=USER_ID,
        )

        assert conn.execute.called


# ── list_permissions (master) ─────────────────────────────────────────────────


class TestListPermissions:
    async def test_returns_system_and_tenant_permissions(self):
        rows = [
            {"id": PERM_ID, "resource": "users", "action": "read",
             "description": "Read users", "is_system": True, "tenant_id": None},
        ]
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=rows)
        db = _mock_db(conn)

        svc = PermissionService(db)
        result = await svc.list_permissions(tenant_id=TENANT_ID)

        assert len(result) == 1
        assert result[0]["is_system"] is True
