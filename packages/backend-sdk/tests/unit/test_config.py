"""Tests for AuthConfig and environment variable validation."""

import pytest
import os
from common_auth.config import AuthConfig
from common_auth.exceptions import ConfigurationError


class TestAuthConfigFromEnv:
    """Test AuthConfig.from_env() method."""

    def test_config_from_env_missing_keycloak_url_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing KEYCLOAK_URL raises ConfigurationError."""
        # Arrange
        monkeypatch.delenv("KEYCLOAK_URL", raising=False)
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act & Assert
        with pytest.raises(ConfigurationError, match="KEYCLOAK_URL"):
            AuthConfig.from_env()

    def test_config_from_env_missing_realm_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing KEYCLOAK_REALM raises ConfigurationError."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.delenv("KEYCLOAK_REALM", raising=False)
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act & Assert
        with pytest.raises(ConfigurationError, match="KEYCLOAK_REALM"):
            AuthConfig.from_env()

    def test_config_from_env_missing_client_id_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing KEYCLOAK_CLIENT_ID raises ConfigurationError."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.delenv("KEYCLOAK_CLIENT_ID", raising=False)

        # Act & Assert
        with pytest.raises(ConfigurationError, match="KEYCLOAK_CLIENT_ID"):
            AuthConfig.from_env()

    def test_config_from_env_invalid_url_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid KEYCLOAK_URL raises ConfigurationError."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "not-a-url")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act & Assert
        with pytest.raises(ConfigurationError, match="valid URL"):
            AuthConfig.from_env()

    def test_config_from_env_valid_config_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that valid environment variables create AuthConfig."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act
        config = AuthConfig.from_env()

        # Assert
        assert config.keycloak_url == "http://localhost:8080"
        assert config.keycloak_realm == "test-realm"
        assert config.keycloak_client_id == "test-client"

    def test_config_from_env_default_values_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that optional environment variables have correct defaults."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act
        config = AuthConfig.from_env()

        # Assert
        assert config.tenant_id_source == "iss"
        assert config.jwks_cache_ttl == 86400
        assert config.enable_rls is True
        assert config.enable_user_sync is False

    def test_config_from_env_custom_optional_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that optional environment variables can be customized."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("TENANT_ID_SOURCE", "custom")
        monkeypatch.setenv("TENANT_ID_CLAIM", "tenant")
        monkeypatch.setenv("JWKS_CACHE_TTL", "3600")
        monkeypatch.setenv("ENABLE_RLS", "false")
        monkeypatch.setenv("ENABLE_USER_SYNC", "true")

        # Act
        config = AuthConfig.from_env()

        # Assert
        assert config.tenant_id_source == "custom"
        assert config.tenant_id_claim == "tenant"
        assert config.jwks_cache_ttl == 3600
        assert config.enable_rls is False
        assert config.enable_user_sync is True

    def test_config_tenant_id_source_custom_requires_claim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TENANT_ID_SOURCE=custom requires TENANT_ID_CLAIM."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("TENANT_ID_SOURCE", "custom")
        monkeypatch.delenv("TENANT_ID_CLAIM", raising=False)

        # Act & Assert
        with pytest.raises(ConfigurationError, match="TENANT_ID_CLAIM"):
            AuthConfig.from_env()

    def test_config_tenant_id_source_fixed_requires_fixed_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TENANT_ID_SOURCE=fixed requires TENANT_ID_FIXED."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("TENANT_ID_SOURCE", "fixed")
        monkeypatch.delenv("TENANT_ID_FIXED", raising=False)

        # Act & Assert
        with pytest.raises(ConfigurationError, match="TENANT_ID_FIXED"):
            AuthConfig.from_env()


class TestAuthConfigProperties:
    """Test AuthConfig property methods."""

    def test_jwks_url_constructed_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that jwks_url property constructs correct URL."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act
        config = AuthConfig.from_env()

        # Assert
        expected = "http://localhost:8080/realms/test-realm/protocol/openid-connect/certs"
        assert config.jwks_url == expected

    def test_issuer_url_constructed_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that issuer property constructs correct issuer URL."""
        # Arrange
        monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
        monkeypatch.setenv("KEYCLOAK_REALM", "test-realm")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")

        # Act
        config = AuthConfig.from_env()

        # Assert
        expected = "http://localhost:8080/realms/test-realm"
        assert config.issuer == expected
