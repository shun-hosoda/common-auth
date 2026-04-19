"""Unit tests for the audit router — GET /admin/audit/logs."""

import uuid
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
from common_auth.routers.audit import router


# ── Fixtures ──────────────────────────────────────────────────────────────────


TENANT_ID = str(uuid.uuid4())


def _make_user(roles: list[str], tenant_id: str = TENANT_ID) -> AuthUser:
    return AuthUser(
        sub=str(uuid.uuid4()),
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
def mock_audit_svc() -> MagicMock:
    m = MagicMock()
    m.list_logs = AsyncMock(return_value=([], 0))
    return m


@contextmanager
def _client(caller: AuthUser, audit_svc: MagicMock) -> Generator[TestClient, None, None]:
    _app = FastAPI()
    _app.include_router(router, prefix="/api/admin")

    # Inject mock DB so the router can create AuditService
    db = MagicMock()
    _app.state.db = db

    _app.dependency_overrides[get_current_user] = lambda: caller

    # Patch AuditService constructor to return our mock
    with patch("common_auth.routers.audit.AuditService", return_value=audit_svc):
        with TestClient(_app) as c:
            yield c


# ── GET /admin/audit/logs ─────────────────────────────────────────────────────


class TestListAuditLogs:
    def test_tenant_admin_gets_logs(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(caller, mock_audit_svc) as c:
            resp = c.get("/api/admin/audit/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 50

    def test_super_admin_without_tenant_id_returns_400(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["super_admin"], tenant_id="")
        with _client(caller, mock_audit_svc) as c:
            resp = c.get("/api/admin/audit/logs")
        assert resp.status_code == 400

    def test_super_admin_with_tenant_id_gets_logs(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["super_admin"], tenant_id="")
        with _client(caller, mock_audit_svc) as c:
            resp = c.get(f"/api/admin/audit/logs?tenant_id={TENANT_ID}")
        assert resp.status_code == 200

    def test_regular_user_gets_403(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["user"])
        with _client(caller, mock_audit_svc) as c:
            resp = c.get("/api/admin/audit/logs")
        assert resp.status_code == 403

    def test_no_db_returns_503(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["tenant_admin"])
        _app = FastAPI()
        _app.include_router(router, prefix="/api/admin")
        # Do NOT set app.state.db
        _app.dependency_overrides[get_current_user] = lambda: caller
        with TestClient(_app) as c:
            resp = c.get("/api/admin/audit/logs")
        assert resp.status_code == 503

    def test_pagination_params_forwarded(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(caller, mock_audit_svc) as c:
            c.get("/api/admin/audit/logs?page=2&per_page=20")
        mock_audit_svc.list_logs.assert_called_once()
        call_kwargs = mock_audit_svc.list_logs.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["per_page"] == 20

    def test_action_filter_forwarded(self, mock_audit_svc: MagicMock) -> None:
        caller = _make_user(["tenant_admin"])
        with _client(caller, mock_audit_svc) as c:
            c.get("/api/admin/audit/logs?action=group.*")
        call_kwargs = mock_audit_svc.list_logs.call_args[1]
        assert call_kwargs["action_prefix"] == "group.*"
