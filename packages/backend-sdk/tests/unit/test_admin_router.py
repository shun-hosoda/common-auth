"""Unit tests for admin router.

These tests use synchronous TestClient (ASGI) with mocked KeycloakAdminClient
so no real Keycloak or network access is required.
"""

import pytest
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from common_auth.dependencies.current_user import get_current_user
from common_auth.routers.admin import router
from common_auth.models.auth_user import AuthUser


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_user(roles: list[str], tenant_id: str = "acme-corp") -> AuthUser:
    return AuthUser(
        sub="caller-123",
        tenant_id=tenant_id,
        email="caller@example.com",
        email_verified=True,
        roles=roles,
        iat=0,
        exp=9_999_999_999,
        iss="http://localhost:8080/realms/common-auth",
        aud="frontend-app",
    )


@pytest.fixture()
def mock_kc() -> MagicMock:
    """Pre-configured mock KeycloakAdminClient."""
    m = MagicMock()
    m.list_users = AsyncMock(
        return_value=[
            {
                "id": "user-456",
                "username": "testuser_acme-corp@example.com",
                "email": "testuser_acme-corp@example.com",
                "firstName": "Test",
                "lastName": "User",
                "enabled": True,
                "emailVerified": True,
                "attributes": {"tenant_id": ["acme-corp"]},
            }
        ]
    )
    m.get_user = AsyncMock(
        return_value={
            "id": "user-456",
            "email": "testuser_acme-corp@example.com",
            "enabled": True,
            "attributes": {"tenant_id": ["acme-corp"]},
        }
    )
    m.create_user = AsyncMock(return_value="new-user-id")
    m.update_user = AsyncMock(return_value=None)
    m.disable_user = AsyncMock(return_value=None)
    m.reset_password = AsyncMock(return_value=None)
    m.reset_mfa = AsyncMock(return_value=None)
    m.find_group_by_name = AsyncMock(
        return_value={"id": "group-acme", "name": "acme-corp"}
    )
    m.add_user_to_group = AsyncMock(return_value=None)
    m.assign_realm_role = AsyncMock(return_value=None)
    m.list_clients = AsyncMock(
        return_value=[
            {
                "id": "client-acme",
                "clientId": "acme-corp",
                "name": "ACME Corp",
                "enabled": True,
            }
        ]
    )
    m.create_client = AsyncMock(return_value="new-client-id")
    return m


@pytest.fixture()
def app(mock_kc: MagicMock) -> FastAPI:
    """FastAPI app with admin router and injected mock."""
    _app = FastAPI()
    _app.include_router(router, prefix="/admin")

    cfg = MagicMock()
    cfg.keycloak_url = "http://localhost:8080"
    cfg.keycloak_realm = "common-auth"
    _app.state.auth_config = cfg
    _app.state.kc_admin_client = mock_kc  # inject mock directly
    return _app


@contextmanager
def _client(app: FastAPI, caller: AuthUser) -> Generator[TestClient, None, None]:
    """Context manager that yields a TestClient with get_current_user overridden.

    Uses FastAPI dependency_overrides so the mock is active during actual
    request processing (patch() exits before the request is dispatched).
    """
    app.dependency_overrides[get_current_user] = lambda: caller
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── GET /admin/users ──────────────────────────────────────────────────────────


class TestListUsers:
    def test_tenant_admin_gets_own_tenant_users(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.get("/admin/users")
        assert resp.status_code == 200
        mock_kc.list_users.assert_called_once_with(tenant_id="acme-corp")

    def test_super_admin_gets_all_users(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.get("/admin/users")
        assert resp.status_code == 200
        mock_kc.list_users.assert_called_once_with(tenant_id=None)

    def test_regular_user_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/admin/users")
        assert resp.status_code == 403


# ── POST /admin/users ─────────────────────────────────────────────────────────


class TestCreateUser:
    def test_tenant_admin_creates_user_in_own_tenant(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/admin/users",
                json={
                    "email": "new@acme-corp.com",
                    "firstName": "New",
                    "lastName": "User",
                    "password": "P@ssw0rd!",
                    "temporary": True,
                },
            )
        assert resp.status_code == 201
        assert resp.json()["id"] == "new-user-id"
        mock_kc.create_user.assert_called_once()
        # Verify tenant_id in payload
        payload = mock_kc.create_user.call_args[0][0]
        assert payload["attributes"]["tenant_id"] == ["acme-corp"]

    def test_regular_user_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.post(
                "/admin/users",
                json={"email": "x@x.com", "password": "abc"},
            )
        assert resp.status_code == 403


# ── DELETE /admin/users/{id} ──────────────────────────────────────────────────


class TestDisableUser:
    def test_tenant_admin_disables_own_tenant_user(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.delete("/admin/users/user-456")
        assert resp.status_code == 200
        mock_kc.disable_user.assert_called_once_with("user-456")

    def test_tenant_admin_cannot_disable_cross_tenant_user(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        # Caller is from globex-inc, target is in acme-corp
        caller = _make_user(["tenant_admin"], tenant_id="globex-inc")
        with _client(app, caller) as c:
            resp = c.delete("/admin/users/user-456")
        assert resp.status_code == 403
        mock_kc.disable_user.assert_not_called()

    def test_cannot_disable_self(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        # Return the caller's own user ID from get_user
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "caller-123",  # same as caller.sub
                "enabled": True,
                "attributes": {"tenant_id": ["acme-corp"]},
            }
        )
        with _client(app, caller) as c:
            resp = c.delete("/admin/users/caller-123")
        assert resp.status_code == 400
        mock_kc.disable_user.assert_not_called()


# ── POST /admin/users/{id}/reset-password ────────────────────────────────────


class TestResetPassword:
    def test_tenant_admin_resets_password(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/admin/users/user-456/reset-password",
                json={"newPassword": "N3wP@ss!", "temporary": True},
            )
        assert resp.status_code == 200
        mock_kc.reset_password.assert_called_once_with("user-456", "N3wP@ss!", True)


# ── POST /admin/users/{id}/reset-mfa ─────────────────────────────────────────


class TestResetMfa:
    def test_tenant_admin_resets_mfa(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post("/admin/users/user-456/reset-mfa")
        assert resp.status_code == 200
        mock_kc.reset_mfa.assert_called_once_with("user-456")


# ── GET /admin/clients ────────────────────────────────────────────────────────


class TestListClients:
    def test_super_admin_lists_clients(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.get("/admin/clients")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["clientId"] == "acme-corp"

    def test_tenant_admin_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.get("/admin/clients")
        assert resp.status_code == 403


# ── POST /admin/clients ───────────────────────────────────────────────────────


class TestCreateClient:
    def test_super_admin_creates_client(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/admin/clients",
                json={"clientId": "new-tenant", "name": "New Tenant"},
            )
        assert resp.status_code == 201
        assert resp.json()["id"] == "new-client-id"

    def test_tenant_admin_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/admin/clients",
                json={"clientId": "evil-tenant"},
            )
        assert resp.status_code == 403
