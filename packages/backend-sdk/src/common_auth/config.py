"""Configuration management for common-auth."""

import os
from typing import Literal
from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings
from common_auth.exceptions import ConfigurationError


class AuthConfig(BaseSettings):
    """Authentication configuration loaded from environment variables."""

    # Required settings
    keycloak_url: str = Field(..., description="Keycloak base URL")
    keycloak_realm: str = Field(..., description="Keycloak realm name")
    keycloak_client_id: str = Field(..., description="Keycloak client ID")

    # Optional settings
    tenant_id_source: Literal["iss", "custom", "fixed"] = Field(
        default="iss",
        description="How to extract tenant_id from JWT"
    )
    tenant_id_claim: str | None = Field(
        default=None,
        description="Custom JWT claim name for tenant_id (when tenant_id_source=custom)"
    )
    tenant_id_fixed: str | None = Field(
        default=None,
        description="Fixed tenant_id value (when tenant_id_source=fixed)"
    )
    jwks_cache_ttl: int = Field(
        default=86400,
        description="JWKS cache TTL in seconds (default 24 hours)",
        ge=60
    )
    enable_rls: bool = Field(
        default=True,
        description="Enable Row-Level Security session variable"
    )
    enable_user_sync: bool = Field(
        default=False,
        description="Enable lazy sync to user_profiles table"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting middleware"
    )

    # SMTP / Email (for invitation mails)
    smtp_host: str = Field(
        default="127.0.0.1",
        description="SMTP server host (use 127.0.0.1 on Windows to avoid IPv6 timeout)"
    )
    smtp_port: int = Field(
        default=1025,
        description="SMTP server port"
    )
    smtp_from: str = Field(
        default="noreply@example.com",
        description="From address for invitation emails"
    )
    smtp_use_tls: bool = Field(
        default=False,
        description="Use STARTTLS for SMTP"
    )
    smtp_username: str | None = Field(
        default=None,
        description="SMTP auth username (optional)"
    )
    smtp_password: str | None = Field(
        default=None,
        description="SMTP auth password (optional)"
    )

    # User invitation settings
    invitation_base_url: str = Field(
        default="http://127.0.0.1:3000",
        description="Base URL for invitation accept links (e.g. https://app.example.com)"
    )
    invitation_expires_hours: int = Field(
        default=72,
        ge=1,
        le=168,
        description="Default invitation token TTL in hours (max 168h = 7 days)"
    )
    keycloak_pw_policy_hint: str = Field(
        default="8文字以上入力してください",
        description="Password policy hint displayed on the invitation accept page"
    )
    rate_limit_default_requests: int = Field(
        default=60,
        ge=1,
        description="Default max requests per minute"
    )
    rate_limit_login_requests: int = Field(
        default=5,
        ge=1,
        description="Max login requests per minute (stricter)"
    )
    rate_limit_trusted_proxies: list[str] = Field(
        default_factory=list,
        description="Trusted proxy CIDR ranges for X-Forwarded-For"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

    @field_validator("keycloak_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that keycloak_url is a valid URL."""
        if not v:
            raise ValueError("KEYCLOAK_URL is required")
        
        # Basic URL validation
        if not v.startswith(("http://", "https://")):
            raise ValueError("KEYCLOAK_URL must be a valid URL starting with http:// or https://")
        
        # Remove trailing slash
        return v.rstrip("/")

    def model_post_init(self, __context: any) -> None:
        """Post-initialization validation."""
        # Validate tenant_id_source dependencies
        if self.tenant_id_source == "custom" and not self.tenant_id_claim:
            raise ConfigurationError(
                "TENANT_ID_SOURCE='custom' requires TENANT_ID_CLAIM to be set"
            )
        
        if self.tenant_id_source == "fixed" and not self.tenant_id_fixed:
            raise ConfigurationError(
                "TENANT_ID_SOURCE='fixed' requires TENANT_ID_FIXED to be set"
            )

    @property
    def jwks_url(self) -> str:
        """Get JWKS URL for public key retrieval."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def issuer(self) -> str:
        """Get expected JWT issuer."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """
        Create AuthConfig from environment variables.
        
        Raises:
            ConfigurationError: If required variables are missing or invalid.
        """
        try:
            return cls()
        except ValidationError as e:
            # Extract first error message
            errors = e.errors()
            if errors:
                first_error = errors[0]
                field_name = first_error["loc"][0]
                msg = first_error["msg"]
                
                # Map field names to environment variable names
                env_var_name = field_name.upper()
                
                if "required" in msg.lower() or "missing" in msg.lower():
                    raise ConfigurationError(
                        f"Configuration error: {env_var_name} is required. "
                        f"Set the environment variable or provide it in AuthConfig."
                    ) from e
                elif "valid URL" in msg:
                    raise ConfigurationError(
                        f"Configuration error: {env_var_name} must be a valid URL. Got: '{os.getenv(env_var_name)}'"
                    ) from e
                else:
                    raise ConfigurationError(
                        f"Configuration error: Invalid value for {env_var_name}. {msg}"
                    ) from e
            
            raise ConfigurationError(f"Configuration error: {str(e)}") from e
