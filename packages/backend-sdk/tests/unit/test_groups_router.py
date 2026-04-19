"""Unit tests for groups router.

Tests verify:
1. Group CRUD endpoints with proper auth
2. Member management endpoints
3. Permission management endpoints
4. 403 for non-admin users
5. 404 for missing resources
"""

import uuid
from datetime import datetime, timezone

import pytest
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from common_auth.dependencies.current_user import get_current_user
from common_auth.routers.groups import router as groups_router
from common_auth.models.auth_user import AuthUser
from common_auth.models.group import (
    GroupResponse,
    GroupListResponse,
    MemberResponse,
    PermissionEntry,
    EffectivePermissionEntry,
)


# 笏笏 Helpers 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


def _make_user(roles: list[str], tenant_id: str = "acme-corp") -> AuthUser:
    return AuthUser(
        sub="00000000-0000-0000-0000-000000000123",
        tenant_id=tenant_id,
        email="caller@example.com",
        email_verified=True,
        roles=roles,
        iat=0,
        exp=9_999_999_999,
        iss="http://localhost:8080/realms/common-auth",
        aud="frontend-app",
    )


_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)
_UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_PERM_UUID = uuid.UUID("00000000-0000-0000-0000-000000000010")

_GROUP_DICT = {
    "id": _UUID1,
    "tenant_id": "acme-corp",
    "name": "Engineering",
    "description": None,
    "parent_group_id": None,
    "is_active": True,
    "sort_order": 0,
    "member_count": 2,
    "created_at": _NOW,
    "updated_at": _NOW,
}

_MEMBER_DICT = {
    "user_id": _UUID1,
    "email": "user@example.com",
    "display_name": "Test User",
    "joined_at": _NOW,
}

_PERM_DICT = {
    "id": _PERM_UUID,
    "resource": "documents",
    "action": "read",
    "description": None,
    "is_system": False,
    "granted": True,
}


def _make_mock_group_service() -> MagicMock:
    svc = MagicMock()
    svc.list_groups = AsyncMock(
        return_value={"items": [_GROUP_DICT], "total": 1, "page": 1, "page_size": 20}
    )
    svc.get_group = AsyncMock(return_value=_GROUP_DICT)
    svc.create_group = AsyncMock(return_value=_GROUP_DICT)
    svc.update_group = AsyncMock(return_value=_GROUP_DICT)
    svc.delete_group = AsyncMock(return_value=True)
    svc.list_members = AsyncMock(
        return_value={"items": [_MEMBER_DICT], "total": 1}
    )
    svc.add_members = AsyncMock(return_value=None)
    svc.remove_member = AsyncMock(return_value=True)
    return svc


def _make_mock_permission_service() -> MagicMock:
    svc = MagicMock()
    svc.list_group_permissions = AsyncMock(return_value=[_PERM_DICT])
    svc.update_group_permissions = AsyncMock(return_value=None)
    svc.get_effective_permissions = AsyncMock(
        return_value=[{
            "id": _PERM_UUID,
            "resource": "documents",
            "action": "read",
            "granted": True,
            "source": "user_direct",
        }]
    )
    return svc


@pytest.fixture()
def mock_group_svc() -> MagicMock:
    return _make_mock_group_service()


@pytest.fixture()
def mock_perm_svc() -> MagicMock:
    return _make_mock_permission_service()


@pytest.fixture()
def app(mock_group_svc: MagicMock, mock_perm_svc: MagicMock) -> FastAPI:
    """FastAPI app with groups_router and mocked services via app.state.db."""
    _app = FastAPI()
    _app.include_router(groups_router, prefix="/api/admin")

    # Create a mock DB that returns mock services when GroupService/PermissionService is init'd
    _app.state.db = MagicMock()

    # Patch constructors so GroupService(db) and PermissionService(db) return our mocks
    _app.state._mock_group_svc = mock_group_svc
    _app.state._mock_perm_svc = mock_perm_svc

    return _app


@contextmanager
def _client(
    app: FastAPI,
    caller: AuthUser,
    mock_group_svc: MagicMock,
    mock_perm_svc: MagicMock,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = lambda: caller
    with (
        patch("common_auth.routers.groups.GroupService", return_value=mock_group_svc),
        patch("common_auth.routers.groups.PermissionService", return_value=mock_perm_svc),
        patch("common_auth.routers.groups.DBClient", MagicMock()),
    ):
        try:
            with TestClient(app, raise_server_exceptions=True) as client:
                yield client
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# 笏笏 GET /admin/groups 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestListGroups:
    def test_tenant_admin_gets_200(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Engineering"

    def test_regular_user_gets_403(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_user"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups")
        assert resp.status_code == 403


# 笏笏 POST /admin/groups 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestCreateGroup:
    def test_tenant_admin_creates_201(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.post("/api/admin/groups", json={"name": "Engineering"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Engineering"


# 笏笏 GET /admin/groups/{id} 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestGetGroup:
    def test_returns_200_when_found(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups/00000000-0000-0000-0000-000000000001")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(_UUID1)

    def test_returns_404_when_not_found(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        mock_group_svc.get_group = AsyncMock(return_value=None)
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404


# 笏笏 PATCH /admin/groups/{id} 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestUpdateGroup:
    def test_update_returns_200(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.put("/api/admin/groups/00000000-0000-0000-0000-000000000001", json={"name": "Infra"})
        assert resp.status_code == 200

    def test_update_nonexistent_404(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        mock_group_svc.update_group = AsyncMock(return_value=None)
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.put("/api/admin/groups/00000000-0000-0000-0000-000000000099", json={"name": "X"})
        assert resp.status_code == 404


# 笏笏 DELETE /admin/groups/{id} 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestDeleteGroup:
    def test_delete_returns_204(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.delete("/api/admin/groups/00000000-0000-0000-0000-000000000001")
        assert resp.status_code == 204

    def test_delete_nonexistent_404(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        mock_group_svc.delete_group = AsyncMock(return_value=False)
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.delete("/api/admin/groups/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404


# 笏笏 GET /admin/groups/{id}/members 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestGetMembers:
    def test_returns_member_list(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups/00000000-0000-0000-0000-000000000001/members")
        assert resp.status_code == 200
        assert resp.json()["items"][0]["user_id"] == str(_UUID1)


# 笏笏 POST /admin/groups/{id}/members 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestAddMembers:
    def test_add_members_returns_204(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.post("/api/admin/groups/00000000-0000-0000-0000-000000000001/members", json={"user_ids": [str(_UUID1), "00000000-0000-0000-0000-000000000003"]})
        assert resp.status_code == 204


# 笏笏 DELETE /admin/groups/{id}/members/{user_id} 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestRemoveMember:
    def test_remove_returns_204(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.delete("/api/admin/groups/00000000-0000-0000-0000-000000000001/members/00000000-0000-0000-0000-000000000001")
        assert resp.status_code == 204

    def test_remove_nonexistent_404(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        mock_group_svc.remove_member = AsyncMock(return_value=False)
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.delete("/api/admin/groups/00000000-0000-0000-0000-000000000001/members/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404


# 笏笏 GET /admin/groups/{id}/permissions 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestGetGroupPermissions:
    def test_returns_permission_list(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.get("/api/admin/groups/00000000-0000-0000-0000-000000000001/permissions")
        assert resp.status_code == 200
        assert resp.json()["permissions"][0]["action"] == "read"


# 笏笏 PUT /admin/groups/{id}/permissions 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏


class TestUpdateGroupPermissions:
    def test_bulk_update_returns_204(
        self, app: FastAPI, mock_group_svc: MagicMock, mock_perm_svc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        payload = {"permissions": [{"permission_id": str(_PERM_UUID), "granted": True}]}
        with _client(app, caller, mock_group_svc, mock_perm_svc) as c:
            resp = c.put("/api/admin/groups/00000000-0000-0000-0000-000000000001/permissions", json=payload)
        assert resp.status_code == 204


