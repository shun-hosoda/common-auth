"""Custom exceptions for common-auth."""


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""

    pass


class TokenInvalidError(AuthenticationError):
    """Raised when JWT token is invalid."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""

    pass


class JWKSError(Exception):
    """Raised when JWKS operations fail."""

    pass


class TenantIsolationError(Exception):
    """Raised when tenant isolation is violated."""

    pass
