"""Route contract test — verifies that all API paths the frontend expects
are actually registered by the backend.

This test catches the class of regression where:
- A new endpoint is added to source code but not wired into a router
- A router prefix is changed without updating the frontend
- An import/include_router call is missing

It runs as a fast unit test (no network, no Docker) by introspecting the
FastAPI route table after setup_auth().
"""

import os
import pytest
from unittest.mock import patch
from fastapi import FastAPI

from common_auth.config import AuthConfig
from common_auth.setup import setup_auth


# ── Expected routes from the frontend (adminApi.ts + vite proxy) ──────────────
# Format: (method, path)
# These MUST match what the React app actually calls.

EXPECTED_ROUTES: list[tuple[str, str]] = [
    # admin router (prefix /api/admin)
    ("GET", "/api/admin/users"),
    ("POST", "/api/admin/users"),
    ("GET", "/api/admin/users/{user_id}"),
    ("PUT", "/api/admin/users/{user_id}"),
    ("DELETE", "/api/admin/users/{user_id}"),
    ("POST", "/api/admin/users/{user_id}/reset-password"),
    ("POST", "/api/admin/users/{user_id}/reset-mfa"),
    ("GET", "/api/admin/clients"),
    ("POST", "/api/admin/clients"),
    ("GET", "/api/admin/security/mfa"),
    ("PUT", "/api/admin/security/mfa"),
    # auth router (prefix /auth)
    ("GET", "/auth/health"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/mfa-status"),
]


@pytest.fixture
def wired_app() -> FastAPI:
    """Create a FastAPI app with setup_auth() applied."""
    app = FastAPI()
    config = AuthConfig(
        keycloak_url="http://localhost:8080",
        keycloak_realm="test-realm",
        keycloak_client_id="test-client",
        rate_limit_enabled=False,
    )
    # Patch JWKS fetch to avoid network calls during route registration
    with patch("common_auth.middleware.jwt_auth.RemoteJWKSService"):
        setup_auth(app, config)
    return app


class TestRouteContract:
    """Verify every frontend-expected route is registered in the backend."""

    def test_all_expected_routes_are_registered(self, wired_app: FastAPI) -> None:
        """Every (method, path) the React frontend calls must exist."""
        registered: set[tuple[str, str]] = set()
        for route in wired_app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    registered.add((method.upper(), route.path))

        missing = []
        for method, path in EXPECTED_ROUTES:
            if (method, path) not in registered:
                missing.append(f"{method} {path}")

        assert missing == [], (
            f"Frontend expects these routes but backend does not register them:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_no_route_prefix_drift(self, wired_app: FastAPI) -> None:
        """Admin routes must start with /api/admin, auth routes with /auth."""
        for route in wired_app.routes:
            if not hasattr(route, "path"):
                continue
            path: str = route.path
            # Skip root / and openapi internal routes
            if path in ("/", "/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"):
                continue
            assert path.startswith(("/api/admin", "/auth")), (
                f"Route {path} does not match expected prefixes /api/admin or /auth. "
                f"If this is intentional, add it to the prefix allowlist."
            )
