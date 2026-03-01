"""
common-auth: Portable authentication SDK based on Keycloak and OIDC.
"""

__version__ = "1.0.0"

from .config import AuthConfig
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    JWKSError,
    TokenExpiredError,
    TokenInvalidError,
)
from .middleware.rate_limit import (
    InMemoryRateLimitStore,
    RateLimitMiddleware,
    RateLimitStore,
)
from .models.auth_user import AuthUser
from .setup import setup_auth

# Dependencies
from .dependencies.current_user import get_current_user, get_optional_user
from .dependencies.tenant import get_tenant_id

__all__ = [
    # Core
    "AuthConfig",
    "setup_auth",
    # Models
    "AuthUser",
    # Rate Limiting
    "RateLimitStore",
    "InMemoryRateLimitStore",
    "RateLimitMiddleware",
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "get_tenant_id",
    # Exceptions
    "AuthenticationError",
    "ConfigurationError",
    "JWKSError",
    "TokenExpiredError",
    "TokenInvalidError",
]
