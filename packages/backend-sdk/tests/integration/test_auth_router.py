"""Integration tests for authentication router."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from datetime import datetime, timedelta

from common_auth import AuthConfig, setup_auth


@pytest.fixture
def rsa_key_pair():
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def create_test_token(rsa_key_pair):
    """Factory to create test JWT tokens."""
    private_key, _ = rsa_key_pair
    
    def _create(
        sub: str = "test-user-id",
        email: str = "test@example.com",
        realm: str = "test-realm",
        roles: list[str] = None
    ) -> str:
        if roles is None:
            roles = ["user"]
        
        now = datetime.utcnow()
        payload = {
            "sub": sub,
            "email": email,
            "email_verified": True,
            "name": "Test User",
            "iss": f"http://localhost:8080/realms/{realm}",
            "aud": "test-client",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "realm_access": {"roles": roles},
        }
        
        return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})
    
    return _create


@pytest.fixture
def app_with_auth(monkeypatch, rsa_key_pair):
    """Create FastAPI app with authentication configured."""
    _, public_key = rsa_key_pair
    
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
    
    config = AuthConfig.from_env()
    
    app = FastAPI()
    
    # Mock JWKS service
    with patch("common_auth.setup.RemoteJWKSService") as mock_jwks_class:
        mock_jwks = AsyncMock()
        mock_jwks.get_public_key.return_value = public_key
        mock_jwks_class.return_value = mock_jwks
        
        # Also patch in middleware
        with patch("common_auth.middleware.jwt_auth.RemoteJWKSService") as mock_jwks_middleware:
            mock_jwks_middleware.return_value = mock_jwks
            setup_auth(app, config)
    
    return app, mock_jwks


class TestAuthRouter:
    """Test authentication router endpoints."""

    def test_health_endpoint_returns_status(self, app_with_auth):
        """Test /auth/health returns health status."""
        app, _ = app_with_auth
        client = TestClient(app)
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.get("/auth/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_me_endpoint_without_auth_returns_401(self, app_with_auth):
        """Test /auth/me without authentication returns 401."""
        app, _ = app_with_auth
        client = TestClient(app)
        
        response = client.get("/auth/me")
        
        assert response.status_code == 401

    def test_me_endpoint_with_valid_token_returns_user_info(
        self,
        app_with_auth,
        create_test_token
    ):
        """Test /auth/me with valid token returns user information."""
        app, _ = app_with_auth
        client = TestClient(app)
        token = create_test_token(
            sub="user-123",
            email="user@example.com",
            roles=["user", "admin"]
        )
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "user-123"
        assert data["email"] == "user@example.com"
        assert data["tenant_id"] == "test-realm"
        assert "user" in data["roles"]
        assert "admin" in data["roles"]

    def test_logout_endpoint_with_auth_returns_204(
        self,
        app_with_auth,
        create_test_token
    ):
        """Test /auth/logout with authentication returns 204."""
        app, _ = app_with_auth
        client = TestClient(app)
        token = create_test_token()
        
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204

    def test_security_headers_applied_to_responses(self, app_with_auth):
        """Test that security headers are applied to all responses."""
        app, _ = app_with_auth
        client = TestClient(app)
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.get("/auth/health")
            
            # Check security headers
            assert "Strict-Transport-Security" in response.headers
            assert "Content-Security-Policy" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-Content-Type-Options" in response.headers
            assert response.headers["X-Frame-Options"] == "DENY"


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_authentication_flow(
        self,
        app_with_auth,
        create_test_token
    ):
        """Test complete authentication flow."""
        app, _ = app_with_auth
        
        # Add a protected endpoint
        from common_auth import get_current_user, AuthUser
        from fastapi import Depends
        
        @app.get("/protected")
        async def protected(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.sub, "tenant": user.tenant_id}
        
        client = TestClient(app)
        
        # 1. Access without token - should fail
        response = client.get("/protected")
        assert response.status_code == 401
        
        # 2. Get token
        token = create_test_token(sub="user-456", email="test@example.com")
        
        # 3. Access with token - should succeed
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-456"
        assert data["tenant"] == "test-realm"
        
        # 4. Verify security headers are present
        assert "Strict-Transport-Security" in response.headers
