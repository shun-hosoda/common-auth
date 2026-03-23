"""Unit tests for auth router — MFA status endpoint.

Tests for GET /auth/mfa-status which returns the current user's MFA
configuration state based on their JWT claims / user attributes.
"""

import pytest
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from common_auth.dependencies.current_user import get_current_user
from common_auth.routers.auth import router
from common_auth.models.auth_user import AuthUser


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_user(
    roles: list[str] | None = None,
    tenant_id: str = "acme-corp",
    extra_claims: dict | None = None,
) -> AuthUser:
    return AuthUser(
        sub="user-001",
        tenant_id=tenant_id,
        email="user@example.com",
        email_verified=True,
        roles=roles or ["user"],
        iat=0,
        exp=9_999_999_999,
        iss="http://localhost:8080/realms/common-auth",
        aud="frontend-app",
        extra_claims=extra_claims or {},
    )


@pytest.fixture()
def mock_kc() -> MagicMock:
    """Pre-configured mock KeycloakAdminClient for auth router tests."""
    m = MagicMock()
    m.get_user = AsyncMock(
        return_value={
            "id": "user-001",
            "email": "user@example.com",
            "enabled": True,
            "attributes": {
                "tenant_id": ["acme-corp"],
                "mfa_enabled": ["false"],
                "mfa_method": ["totp"],
            },
            "requiredActions": [],
            "credentials": [],
        }
    )
    return m


@pytest.fixture()
def app(mock_kc: MagicMock) -> FastAPI:
    """FastAPI app with auth router and injected mock."""
    _app = FastAPI()
    _app.include_router(router, prefix="/api/auth")

    cfg = MagicMock()
    cfg.keycloak_url = "http://localhost:8080"
    cfg.keycloak_realm = "common-auth"
    _app.state.auth_config = cfg
    _app.state.kc_admin_client = mock_kc
    return _app


@contextmanager
def _client(app: FastAPI, caller: AuthUser) -> Generator[TestClient, None, None]:
    """Context manager that yields a TestClient with get_current_user overridden."""
    app.dependency_overrides[get_current_user] = lambda: caller
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── GET /auth/mfa-status — MFA disabled tenant ───────────────────────────────


class TestMfaStatusDisabledTenant:
    """Task 2-7: MFA disabled tenant returns disabled status."""

    def test_mfa_disabled_tenant(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "user-001",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["false"],
                    "mfa_method": ["totp"],
                },
                "requiredActions": [],
            }
        )
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is False
        assert data["mfa_method"] == "totp"
        assert data["mfa_configured"] is False

    def test_mfa_disabled_no_mfa_attrs(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        """User without any MFA attributes → disabled."""
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "user-001",
                "attributes": {"tenant_id": ["acme-corp"]},
                "requiredActions": [],
            }
        )
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is False
        assert data["mfa_method"] == "totp"
        assert data["mfa_configured"] is False


# ── GET /auth/mfa-status — TOTP configured ───────────────────────────────────


class TestMfaStatusTotpConfigured:
    """Task 2-7: MFA enabled + TOTP + OTP credential present."""

    def test_totp_configured(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "user-001",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
                "requiredActions": [],
            }
        )
        mock_kc.get_user_credentials = AsyncMock(
            return_value=[{"id": "cred-1", "type": "otp"}]
        )
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "totp"
        assert data["mfa_configured"] is True


# ── GET /auth/mfa-status — TOTP not configured ───────────────────────────────


class TestMfaStatusTotpNotConfigured:
    """Task 2-7: MFA enabled + TOTP + no OTP credential (pending setup)."""

    def test_totp_not_configured(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "user-001",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["totp"],
                },
                "requiredActions": ["CONFIGURE_TOTP"],
            }
        )
        mock_kc.get_user_credentials = AsyncMock(return_value=[])
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "totp"
        assert data["mfa_configured"] is False


# ── GET /auth/mfa-status — Email OTP ─────────────────────────────────────────


class TestMfaStatusEmailOtp:
    """Task 2-7: MFA enabled + Email OTP."""

    def test_email_otp(
        self, app: FastAPI, mock_kc: MagicMock
    ) -> None:
        mock_kc.get_user = AsyncMock(
            return_value={
                "id": "user-001",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "mfa_enabled": ["true"],
                    "mfa_method": ["email"],
                },
                "requiredActions": [],
            }
        )
        caller = _make_user(["user"])
        with _client(app, caller) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "email"
        # Email OTP does not require user-side credential setup
        assert data["mfa_configured"] is True


# ── GET /auth/mfa-status — Authentication check ──────────────────────────────


class TestMfaStatusAuthCheck:
    """Task 2-8: Unauthenticated user gets 401."""

    def test_unauthenticated_401(self, app: FastAPI) -> None:
        """Without dependency override, get_current_user raises 401."""
        # Don't override get_current_user → default dependency tries request.state.user
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/auth/mfa-status")
        assert resp.status_code == 401


# ── GET /auth/mfa-status — Admin API not configured ──────────────────────────


class TestMfaStatusAdminNotConfigured:
    """When admin client is not on app.state, return 503."""

    def test_admin_not_configured_503(self) -> None:
        _app = FastAPI()
        _app.include_router(router, prefix="/api/auth")
        cfg = MagicMock()
        cfg.keycloak_url = "http://localhost:8080"
        cfg.keycloak_realm = "common-auth"
        _app.state.auth_config = cfg
        # Deliberately NOT setting _app.state.kc_admin_client

        caller = _make_user(["user"])
        _app.dependency_overrides[get_current_user] = lambda: caller
        try:
            with TestClient(_app, raise_server_exceptions=False) as c:
                resp = c.get("/api/auth/mfa-status")
            assert resp.status_code == 503
        finally:
            _app.dependency_overrides.pop(get_current_user, None)
