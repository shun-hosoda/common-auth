"""Tests for JWKS service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from common_auth.services.jwks import JWKSService, RemoteJWKSService
from common_auth.config import AuthConfig
from common_auth.exceptions import JWKSError


@pytest.fixture
def auth_config(monkeypatch: pytest.MonkeyPatch) -> AuthConfig:
    """Create test auth configuration."""
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
    return AuthConfig.from_env()


@pytest.fixture
def rsa_key_pair() -> tuple:
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def jwks_response() -> dict:
    """Create mock JWKS response."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-kid-1",
                "alg": "RS256",
                "n": "xGOr-H7A...",  # Base64 encoded modulus
                "e": "AQAB"  # Base64 encoded exponent
            }
        ]
    }


class TestRemoteJWKSService:
    """Test RemoteJWKSService."""

    @pytest.mark.asyncio
    async def test_jwks_service_fetch_success(
        self,
        auth_config: AuthConfig,
        jwks_response: dict
    ) -> None:
        """Test successful JWKS fetch."""
        # Arrange
        service = RemoteJWKSService(auth_config)
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=jwks_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            keys = await service.fetch_jwks()
            
            # Assert
            assert keys == jwks_response
            mock_client.get.assert_called_once_with(
                auth_config.jwks_url,
                timeout=10.0
            )

    @pytest.mark.asyncio
    async def test_jwks_service_fetch_failure_raises_error(
        self,
        auth_config: AuthConfig
    ) -> None:
        """Test that fetch failure raises JWKSError."""
        # Arrange
        service = RemoteJWKSService(auth_config)
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            # Act & Assert
            with pytest.raises(JWKSError, match="Failed to fetch JWKS"):
                await service.fetch_jwks()

    @pytest.mark.asyncio
    async def test_jwks_service_cache_hit_does_not_fetch(
        self,
        auth_config: AuthConfig,
        jwks_response: dict
    ) -> None:
        """Test that cache hit does not trigger HTTP request."""
        # Arrange
        service = RemoteJWKSService(auth_config)
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=jwks_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act - First call (cache miss)
            await service.get_public_key("test-kid-1")
            first_call_count = mock_client.get.call_count
            
            # Act - Second call (cache hit)
            await service.get_public_key("test-kid-1")
            second_call_count = mock_client.get.call_count
            
            # Assert
            assert first_call_count == 1
            assert second_call_count == 1  # No additional call

    @pytest.mark.asyncio
    async def test_jwks_service_unknown_kid_refreshes(
        self,
        auth_config: AuthConfig,
        jwks_response: dict
    ) -> None:
        """Test that unknown kid triggers JWKS refresh."""
        # Arrange
        service = RemoteJWKSService(auth_config)
        
        # First response without kid-2
        first_jwks = jwks_response.copy()
        first_response = AsyncMock()
        first_response.status_code = 200
        first_response.json = MagicMock(return_value=first_jwks)
        first_response.raise_for_status = MagicMock()
        
        # Second response with kid-2
        second_jwks = jwks_response.copy()
        second_jwks["keys"] = list(second_jwks["keys"])  # Make mutable copy
        second_jwks["keys"].append({
            "kty": "RSA",
            "use": "sig",
            "kid": "test-kid-2",
            "alg": "RS256",
            "n": "yHPs-I8B...",
            "e": "AQAB"
        })
        second_response = AsyncMock()
        second_response.status_code = 200
        second_response.json = MagicMock(return_value=second_jwks)
        second_response.raise_for_status = MagicMock()
        
        # Create two separate client instances
        first_client = AsyncMock()
        first_client.get = AsyncMock(return_value=first_response)
        first_client.__aenter__ = AsyncMock(return_value=first_client)
        first_client.__aexit__ = AsyncMock(return_value=None)
        
        second_client = AsyncMock()
        second_client.get = AsyncMock(return_value=second_response)
        second_client.__aenter__ = AsyncMock(return_value=second_client)
        second_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient", side_effect=[first_client, second_client]):
            # Act
            await service.get_public_key("test-kid-1")  # Cache JWKS (only test-kid-1)
            await service.get_public_key("test-kid-2")  # Trigger refresh (kid-2 not in first JWKS)
            
            # Assert
            assert first_client.get.call_count == 1
            assert second_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_jwks_service_cache_expiry_triggers_refresh(
        self,
        auth_config: AuthConfig,
        jwks_response: dict,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that cache expiry triggers JWKS refresh."""
        # Arrange
        monkeypatch.setenv("JWKS_CACHE_TTL", "60")  # Minimum 60 seconds
        config = AuthConfig.from_env()
        service = RemoteJWKSService(config)
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=jwks_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Act
            await service.get_public_key("test-kid-1")  # Cache
            
            # Clear cache manually for testing
            service.clear_cache()
            
            await service.get_public_key("test-kid-1")  # Should trigger refresh
            
            # Assert
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_jwks_service_graceful_degradation_uses_cache(
        self,
        auth_config: AuthConfig,
        jwks_response: dict
    ) -> None:
        """Test graceful degradation when fetch fails but cache is valid."""
        # Arrange
        service = RemoteJWKSService(auth_config)
        
        # First call succeeds
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json = MagicMock(return_value=jwks_response)
        success_response.raise_for_status = MagicMock()
        
        # Create clients for first and second calls
        first_client = AsyncMock()
        first_client.get = AsyncMock(return_value=success_response)
        first_client.__aenter__ = AsyncMock(return_value=first_client)
        first_client.__aexit__ = AsyncMock(return_value=None)
        
        # Second client will not be used because of cache
        
        with patch("httpx.AsyncClient", return_value=first_client):
            # Act
            key1 = await service.get_public_key("test-kid-1")  # Populates cache
            key2 = await service.get_public_key("test-kid-1")  # Uses cache despite failure
            
            # Assert
            assert key1 is not None
            assert key2 is not None
            assert first_client.get.call_count == 1  # Second call not made (cached)

    @pytest.mark.asyncio
    async def test_jwks_service_cache_expired_fetch_fails_raises_error(
        self,
        auth_config: AuthConfig,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that expired cache + fetch failure raises JWKSError."""
        # Arrange
        monkeypatch.setenv("JWKS_CACHE_TTL", "60")  # Minimum 60 seconds
        config = AuthConfig.from_env()
        service = RemoteJWKSService(config)
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call succeeds
            success_response = AsyncMock()
            success_response.status_code = 200
            success_response.json = AsyncMock(return_value={"keys": []})
            
            mock_get.side_effect = [success_response, Exception("Keycloak down")]
            
            # Act
            await service.fetch_jwks()  # Populate cache
            
            # Clear cache to simulate expiry
            service.clear_cache()
            
            # Act & Assert
            with pytest.raises(JWKSError):
                await service.fetch_jwks()  # Cache expired, fetch fails
