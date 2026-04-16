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
    # MFA-related mocks (Step 2)
    m.get_group = AsyncMock(
        return_value={
            "id": "group-acme",
            "name": "acme-corp",
            "attributes": {
                "tenant_id": ["acme-corp"],
                "mfa_enabled": ["false"],
                "mfa_method": ["totp"],
            },
        }
    )
    m.update_group_attributes = AsyncMock(return_value=None)
    m.set_user_attributes_bulk = AsyncMock(return_value=[])
    m.add_required_action_bulk = AsyncMock(return_value=[])
    m.remove_required_action_bulk = AsyncMock(return_value=[])
    m.get_user_credentials = AsyncMock(return_value=[])
    return m


@pytest.fixture()
def app(mock_kc: MagicMock) -> FastAPI:
    """FastAPI app with admin router and injected mock."""
    _app = FastAPI()
    _app.include_router(router, prefix="/api/admin")

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
            resp = c.get("/api/admin/users")
        assert resp.status_code == 200
        mock_kc.list_users.assert_called_once_with(tenant_id="acme-corp")

    def test_super_admin_gets_all_users(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/users")
        assert resp.status_code == 200
        mock_kc.list_users.assert_called_once_with(tenant_id=None)

    def test_regular_user_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/users")
        assert resp.status_code == 403


# ── POST /admin/users ─────────────────────────────────────────────────────────


class TestCreateUser:
    def test_tenant_admin_creates_user_in_own_tenant(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/users",
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
                "/api/admin/users",
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
            resp = c.delete("/api/admin/users/user-456")
        assert resp.status_code == 200
        mock_kc.disable_user.assert_called_once_with("user-456")

    def test_tenant_admin_cannot_disable_cross_tenant_user(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        # Caller is from globex-inc, target is in acme-corp
        caller = _make_user(["tenant_admin"], tenant_id="globex-inc")
        with _client(app, caller) as c:
            resp = c.delete("/api/admin/users/user-456")
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
            resp = c.delete("/api/admin/users/caller-123")
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
                "/api/admin/users/user-456/reset-password",
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
            resp = c.post("/api/admin/users/user-456/reset-mfa")
        assert resp.status_code == 200
        mock_kc.reset_mfa.assert_called_once_with("user-456")


# ── GET /admin/clients ────────────────────────────────────────────────────────


class TestListClients:
    def test_super_admin_lists_clients(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/clients")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["clientId"] == "acme-corp"

    def test_tenant_admin_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/clients")
        assert resp.status_code == 403


# ── POST /admin/clients ───────────────────────────────────────────────────────


class TestCreateClient:
    def test_super_admin_creates_client(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/clients",
                json={"clientId": "new-tenant", "name": "New Tenant"},
            )
        assert resp.status_code == 201
        assert resp.json()["id"] == "new-client-id"

    def test_tenant_admin_is_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/clients",
                json={"clientId": "evil-tenant"},
            )
        assert resp.status_code == 403


# ── GET /admin/security/mfa ──────────────────────────────────────────────────


class TestGetMfaSettings:
    """Task 2-1: GET /security/mfa returns current tenant MFA settings."""

    def test_initial_state_disabled(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Default state: mfa_enabled=false, mfa_method=totp."""
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/security/mfa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is False
        assert data["mfa_method"] == "totp"
        # Verify 2-stage group lookup
        mock_kc.find_group_by_name.assert_called_once_with("acme-corp")
        mock_kc.get_group.assert_called_once_with("group-acme")

    def test_enabled_state(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """When MFA is enabled, returns mfa_enabled=true."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["email"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/security/mfa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "email"

    def test_user_role_forbidden(self, app: FastAPI) -> None:
        """Regular user cannot access security settings."""
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/security/mfa")
        assert resp.status_code == 403

    def test_super_admin_accesses_any_tenant(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        caller = _make_user(["super_admin"])
        with _client(app, caller) as c:
            resp = c.get("/api/admin/security/mfa")
        assert resp.status_code == 200


# ── PUT /admin/security/mfa — Enable ─────────────────────────────────────────


class TestPutMfaEnable:
    """Task 2-2: Enable MFA for a tenant."""

    def test_enable_totp(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Enable MFA with TOTP method."""
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "updated"
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "totp"
        assert "users_updated" in data
        assert "users_failed" in data

        # Group attributes updated
        mock_kc.update_group_attributes.assert_called_once_with(
            "group-acme",
            {"mfa_enabled": ["true"], "mfa_method": ["totp"]},
        )
        # User attributes set
        mock_kc.set_user_attributes_bulk.assert_called_once()
        # CONFIGURE_TOTP added for totp
        mock_kc.add_required_action_bulk.assert_called_once()
        assert mock_kc.add_required_action_bulk.call_args[0][1] == "CONFIGURE_TOTP"

    def test_enable_email(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Enable MFA with Email method."""
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "email"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "email"

        # Email method should remove CONFIGURE_TOTP, not add
        mock_kc.remove_required_action_bulk.assert_called_once()
        assert mock_kc.remove_required_action_bulk.call_args[0][1] == "CONFIGURE_TOTP"


# ── PUT /admin/security/mfa — Disable ────────────────────────────────────────


class TestPutMfaDisable:
    """Task 2-3: Disable MFA for a tenant."""

    def test_disable_mfa(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Disable MFA — attributes updated, CONFIGURE_TOTP removed."""
        # Start with MFA enabled
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": False, "mfa_method": "totp"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is False

        # Group attributes updated to disabled
        mock_kc.update_group_attributes.assert_called_once_with(
            "group-acme",
            {"mfa_enabled": ["false"], "mfa_method": ["totp"]},
        )
        # User attrs: mfa_enabled=false, mfa_method preserved (for re-enable)
        mock_kc.set_user_attributes_bulk.assert_called_once()
        attrs = mock_kc.set_user_attributes_bulk.call_args[0][1]
        assert attrs["mfa_enabled"] == ["false"]
        assert attrs["mfa_method"] == ["totp"]
        # CONFIGURE_TOTP and email-authenticator-setup both removed on disable
        assert mock_kc.remove_required_action_bulk.call_count == 2
        removed_actions = [c.args[1] for c in mock_kc.remove_required_action_bulk.call_args_list]
        assert "CONFIGURE_TOTP" in removed_actions
        assert "email-authenticator-setup" in removed_actions


# ── PUT /admin/security/mfa — Method change ──────────────────────────────────


class TestPutMfaMethodChange:
    """Task 2-4: Change MFA method triggers credential reset."""

    def test_totp_to_email_resets_mfa(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Changing from TOTP→Email with mfa_enabled=true should reset OTP creds."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "email"},
            )
        assert resp.status_code == 200
        # MFA reset should be called for each user (method change)
        mock_kc.reset_mfa.assert_called()
        # Email → remove CONFIGURE_TOTP
        mock_kc.remove_required_action_bulk.assert_called_once()

    def test_email_to_totp(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Changing from Email→TOTP with mfa_enabled=true should reset and add CONFIGURE_TOTP."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["email"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        assert resp.status_code == 200
        # MFA reset should be called for method change
        mock_kc.reset_mfa.assert_called()
        # TOTP → add CONFIGURE_TOTP
        mock_kc.add_required_action_bulk.assert_called_once()

    def test_no_reset_when_method_unchanged(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """Same method (totp→totp) should NOT trigger MFA reset."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        assert resp.status_code == 200
        # No method change → no reset
        mock_kc.reset_mfa.assert_not_called()


# ── PUT /admin/security/mfa — Auth check ─────────────────────────────────────


class TestPutMfaAuthCheck:
    """Task 2-5: Permission checks for PUT /security/mfa."""

    def test_user_role_forbidden(self, app: FastAPI) -> None:
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        assert resp.status_code == 403

    def test_nonexistent_tenant_group_returns_404(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """tenant_admin from globex-inc — group not found returns 404."""
        mock_kc.find_group_by_name = AsyncMock(return_value=None)
        caller = _make_user(["tenant_admin"], tenant_id="globex-inc")
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        # find_group_by_name("globex-inc") returns None → 404
        assert resp.status_code == 404


# ── PUT /admin/security/mfa — Partial failure ────────────────────────────────


class TestPutMfaPartialFailure:
    """Task 2-6: Some user updates fail → users_failed count."""

    def test_partial_failure_reports_count(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """One user fails attr update → users_failed=1."""
        mock_kc.list_users = AsyncMock(
            return_value=[
                {"id": "u1", "attributes": {"tenant_id": ["acme-corp"]}},
                {"id": "u2", "attributes": {"tenant_id": ["acme-corp"]}},
                {"id": "u3", "attributes": {"tenant_id": ["acme-corp"]}},
            ]
        )
        # set_user_attributes_bulk returns 1 failed user
        mock_kc.set_user_attributes_bulk = AsyncMock(return_value=["u2"])
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.put(
                "/api/admin/security/mfa",
                json={"mfa_enabled": True, "mfa_method": "totp"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["users_updated"] == 2  # 3 total - 1 failed
        assert data["users_failed"] == 1


# ── POST /admin/users — MFA extension ────────────────────────────────────────


class TestCreateUserMfaExtension:
    """Task 2-9: create_user extends new user with MFA attributes when tenant MFA is enabled."""

    def test_mfa_enabled_tenant_totp(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """New user in MFA-enabled TOTP tenant gets MFA attrs + CONFIGURE_TOTP."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/users",
                json={
                    "email": "new@acme-corp.com",
                    "firstName": "New",
                    "lastName": "User",
                    "password": "P@ssw0rd!",
                    "temporary": True,
                },
            )
        assert resp.status_code == 201
        # Verify update_user was called with MFA attrs + requiredActions
        mock_kc.update_user.assert_called_once()
        call_args = mock_kc.update_user.call_args
        payload = call_args[0][1]
        assert payload["attributes"]["mfa_enabled"] == ["true"]
        assert payload["attributes"]["mfa_method"] == ["totp"]
        assert "CONFIGURE_TOTP" in payload["requiredActions"]

    def test_mfa_enabled_tenant_email(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """New user in MFA-enabled Email tenant gets MFA attrs but no CONFIGURE_TOTP."""
        mock_kc.get_group = AsyncMock(
            return_value={
                "id": "group-acme",
                "name": "acme-corp",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["email"],
                },
            }
        )
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/users",
                json={
                    "email": "new@acme-corp.com",
                    "firstName": "New",
                    "lastName": "User",
                    "password": "P@ssw0rd!",
                    "temporary": True,
                },
            )
        assert resp.status_code == 201
        mock_kc.update_user.assert_called_once()
        payload = mock_kc.update_user.call_args[0][1]
        assert payload["attributes"]["mfa_enabled"] == ["true"]
        assert payload["attributes"]["mfa_method"] == ["email"]
        assert payload["requiredActions"] == []

    def test_mfa_disabled_tenant_no_extra_update(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """New user in MFA-disabled tenant should not get extra update_user call."""
        caller = _make_user(["tenant_admin"])
        with _client(app, caller) as c:
            resp = c.post(
                "/api/admin/users",
                json={
                    "email": "new@acme-corp.com",
                    "firstName": "New",
                    "lastName": "User",
                    "password": "P@ssw0rd!",
                    "temporary": True,
                },
            )
        assert resp.status_code == 201
        # update_user should NOT be called (only create_user)
        mock_kc.update_user.assert_not_called()
