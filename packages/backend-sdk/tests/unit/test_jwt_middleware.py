import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from common_auth.config import AuthConfig
from common_auth.middleware.jwt_auth import JWTAuthMiddleware
from common_auth.exceptions import TokenInvalidError, TokenExpiredError


@pytest.fixture
def rsa_private_key():
    """Generate RSA private key for testing."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def rsa_public_key(rsa_private_key):
    """Get RSA public key from private key."""
    return rsa_private_key.public_key()


@pytest.fixture
def create_jwt_token(rsa_private_key):
    """Factory to create JWT tokens."""
    def _create(
        sub: str = "test-user-id",
        email: str = "test@example.com",
        realm: str = "test-realm",
        expired: bool = False,
        invalid_signature: bool = False
    ) -> str:
        now = datetime.now(timezone.utc)
        exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
        
        payload = {
            "sub": sub,
            "email": email,
            "email_verified": True,
            "iss": f"http://localhost:8080/realms/{realm}",
            "aud": "test-client",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "realm_access": {"roles": ["user"]},
        }
        
        if invalid_signature:
            # Use a different key for invalid signature
            wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            return jwt.encode(payload, wrong_key, algorithm="RS256", headers={"kid": "test-kid"})
        
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": "test-kid"})
    
    return _create


class TestJWTAuthMiddleware:
    """Test JWT authentication middleware."""

    @pytest.mark.asyncio
    async def test_jwt_auth_valid_token_sets_request_state(
        self,
        monkeypatch: pytest.MonkeyPatch,
        create_jwt_token,
        rsa_public_key
    ) -> None:
        """Test that valid token sets request.state.user."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        token = create_jwt_token()
        
        # Mock JWKS service
        with patch("common_auth.middleware.jwt_auth.RemoteJWKSService") as MockJWKS:
            mock_service = AsyncMock()
            mock_service.get_public_key.return_value = rsa_public_key
            MockJWKS.return_value = mock_service
            
            app = FastAPI()
            app.add_middleware(JWTAuthMiddleware, config=config)
            
            @app.get("/test")
            async def test_endpoint(request: Request):
                user = request.state.user
                return {"sub": user.sub, "email": user.email}
            
            # Act
            client = TestClient(app)
            response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["sub"] == "test-user-id"
            assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_jwt_auth_missing_header_returns_401(
        self,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing Authorization header returns 401."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        
        app = FastAPI()
        app.add_middleware(JWTAuthMiddleware, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        # Act
        client = TestClient(app)
        response = client.get("/test")
        
        # Assert
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_jwt_auth_invalid_format_returns_401(
        self,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid token format returns 401."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        
        app = FastAPI()
        app.add_middleware(JWTAuthMiddleware, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        # Act
        client = TestClient(app)
        response = client.get("/test", headers={"Authorization": "InvalidFormat token"})
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_expired_token_returns_401(
        self,
        monkeypatch: pytest.MonkeyPatch,
        create_jwt_token,
        rsa_public_key
    ) -> None:
        """Test that expired token returns 401."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        token = create_jwt_token(expired=True)
        
        with patch("common_auth.middleware.jwt_auth.RemoteJWKSService") as MockJWKS:
            mock_service = AsyncMock()
            mock_service.get_public_key.return_value = rsa_public_key
            MockJWKS.return_value = mock_service
            
            app = FastAPI()
            app.add_middleware(JWTAuthMiddleware, config=config)
            
            @app.get("/test")
            async def test_endpoint():
                return {"message": "success"}
            
            # Act
            client = TestClient(app)
            response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            
            # Assert
            assert response.status_code == 401
            assert "expired" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_jwt_auth_invalid_signature_returns_401(
        self,
        monkeypatch: pytest.MonkeyPatch,
        create_jwt_token,
        rsa_public_key
    ) -> None:
        """Test that invalid signature returns 401."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        token = create_jwt_token(invalid_signature=True)
        
        with patch("common_auth.middleware.jwt_auth.RemoteJWKSService") as MockJWKS:
            mock_service = AsyncMock()
            mock_service.get_public_key.return_value = rsa_public_key
            MockJWKS.return_value = mock_service
            
            app = FastAPI()
            app.add_middleware(JWTAuthMiddleware, config=config)
            
            @app.get("/test")
            async def test_endpoint():
                return {"message": "success"}
            
            # Act
            client = TestClient(app)
            response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            
            # Assert
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_tenant_id_extracted_from_iss(
        self,
        monkeypatch: pytest.MonkeyPatch,
        create_jwt_token,
        rsa_public_key
    ) -> None:
        """Test that tenant_id is extracted from iss claim."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "tenant-a")  # Match token realm
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        
        config = AuthConfig.from_env()
        token = create_jwt_token(realm="tenant-a")
        
        with patch("common_auth.middleware.jwt_auth.RemoteJWKSService") as MockJWKS:
            mock_service = AsyncMock()
            mock_service.get_public_key.return_value = rsa_public_key
            MockJWKS.return_value = mock_service
            
            app = FastAPI()
            app.add_middleware(JWTAuthMiddleware, config=config)
            
            @app.get("/test")
            async def test_endpoint(request: Request):
                return {"tenant_id": request.state.tenant_id}
            
            # Act
            client = TestClient(app)
            response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            
            # Assert
            assert response.status_code == 200
            assert response.json()["tenant_id"] == "tenant-a"
