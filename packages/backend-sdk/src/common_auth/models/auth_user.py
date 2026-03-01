"""Authentication user model."""

from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime


class AuthUser(BaseModel):
    """
    Authenticated user model representing JWT token claims.
    
    This model is populated from JWT claims after successful verification
    and stored in request.state.user.
    """

    sub: str = Field(..., description="Subject (user ID) from Keycloak")
    tenant_id: str = Field(..., description="Tenant identifier")
    email: str = Field(..., description="User email address")
    email_verified: bool = Field(default=False, description="Email verification status")
    display_name: str | None = Field(default=None, description="Display name")
    given_name: str | None = Field(default=None, description="Given name")
    family_name: str | None = Field(default=None, description="Family name")
    roles: list[str] = Field(default_factory=list, description="User roles")
    
    # Token metadata
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    exp: int = Field(..., description="Expiration time (Unix timestamp)")
    iss: str = Field(..., description="Issuer URL")
    aud: str | list[str] = Field(..., description="Audience")
    
    # Additional claims
    extra_claims: dict[str, Any] = Field(default_factory=dict, description="Additional JWT claims")

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow().timestamp() > self.exp

    @property
    def has_role(self) -> Any:
        """Return a function to check if user has a specific role."""
        def check(role: str) -> bool:
            return role in self.roles
        return check

    model_config = {
        "extra": "allow"  # Allow extra fields for additional claims
    }
