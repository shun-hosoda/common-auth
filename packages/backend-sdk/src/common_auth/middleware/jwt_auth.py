"""JWT authentication middleware for FastAPI."""

import logging
from typing import Callable
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from common_auth.config import AuthConfig
from common_auth.models.auth_user import AuthUser
from common_auth.services.jwks import RemoteJWKSService
from common_auth.exceptions import TokenExpiredError, TokenInvalidError

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT token verification.
    
    This middleware:
    1. Extracts JWT from Authorization header
    2. Verifies signature using JWKS
    3. Validates claims (exp, iss, aud)
    4. Sets request.state.user and request.state.tenant_id
    
    Unauthenticated requests return 401.

    Paths listed in ``excluded_paths`` are skipped entirely (Public endpoints
    such as the invitation accept/validate APIs).
    """

    #: Paths that never require authentication.
    #: Exact prefix-match: a path is excluded if it starts with any entry.
    DEFAULT_EXCLUDED_PREFIXES: tuple[str, ...] = (
        "/auth/health",
        "/api/invitations/validate",
        "/api/invitations/accept",
    )

    def __init__(
        self,
        app,
        config: AuthConfig,
        *,
        extra_excluded_prefixes: tuple[str, ...] = (),
    ) -> None:
        """
        Initialize JWT authentication middleware.
        
        Args:
            app: FastAPI application
            config: Authentication configuration
            extra_excluded_prefixes: Additional path prefixes to skip auth for.
        """
        super().__init__(app)
        self.config = config
        self.jwks_service = RemoteJWKSService(config)
        self._excluded = self.DEFAULT_EXCLUDED_PREFIXES + extra_excluded_prefixes
        logger.info("Initialized JWTAuthMiddleware (excluded: %s)", self._excluded)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and verify JWT.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip authentication for excluded paths (health check, public invitation API, etc.)
        if any(request.url.path.startswith(prefix) for prefix in self._excluded):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return self._unauthorized_response("Missing authorization header")
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return self._unauthorized_response("Invalid token format")
        
        token = parts[1]
        
        # Verify and decode JWT
        try:
            user = await self._verify_token(token)
        except ExpiredSignatureError:
            logger.warning(f"Token expired for path: {request.url.path}")
            return self._unauthorized_response("Token expired")
        except TokenInvalidError as e:
            logger.warning(f"Invalid token for path: {request.url.path}: {e}")
            return self._unauthorized_response(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return self._error_response("Authentication service error", status_code=500)

        # Set user and tenant_id in request state
        request.state.user = user
        request.state.tenant_id = user.tenant_id

        logger.debug(f"Authenticated user: {user.sub}, tenant: {user.tenant_id}")

        return await call_next(request)

    async def _verify_token(self, token: str) -> AuthUser:
        """
        Verify JWT token and extract user information.
        
        Args:
            token: JWT token string
            
        Returns:
            Authenticated user model
            
        Raises:
            TokenInvalidError: If token is invalid
            TokenExpiredError: If token has expired
        """
        # Decode header to get kid
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise TokenInvalidError("Token missing 'kid' in header")
        except Exception as e:
            raise TokenInvalidError(f"Failed to decode token header: {e}") from e
        
        # Get public key from JWKS
        public_key = await self.jwks_service.get_public_key(kid)
        
        # Verify and decode token
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.config.keycloak_client_id,
                issuer=self.config.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
        except ExpiredSignatureError:
            raise
        except InvalidTokenError as e:
            raise TokenInvalidError(f"Token verification failed: {e}") from e
        
        # Extract tenant_id based on configuration
        tenant_id = self._extract_tenant_id(payload)
        
        # Extract roles
        roles = []
        realm_access = payload.get("realm_access", {})
        if isinstance(realm_access, dict):
            roles = realm_access.get("roles", [])
        
        # Create AuthUser model
        user = AuthUser(
            sub=payload["sub"],
            tenant_id=tenant_id,
            email=payload.get("email", ""),
            email_verified=payload.get("email_verified", False),
            display_name=payload.get("name"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
            roles=roles,
            iat=payload["iat"],
            exp=payload["exp"],
            iss=payload["iss"],
            aud=payload["aud"],
            extra_claims={k: v for k, v in payload.items() if k not in [
                "sub", "email", "email_verified", "name", "given_name", 
                "family_name", "iat", "exp", "iss", "aud", "realm_access"
            ]}
        )
        
        return user

    def _extract_tenant_id(self, payload: dict) -> str:
        """
        Extract tenant ID from JWT payload.
        
        Args:
            payload: Decoded JWT payload
            
        Returns:
            Tenant ID
            
        Raises:
            TokenInvalidError: If tenant_id cannot be extracted
        """
        if self.config.tenant_id_source == "iss":
            # Extract realm name from issuer URL
            # Format: http://localhost:8080/realms/tenant-name
            iss = payload.get("iss", "")
            parts = iss.rstrip("/").split("/")
            if len(parts) >= 2 and parts[-2] == "realms":
                return parts[-1]
            raise TokenInvalidError(f"Cannot extract realm name from issuer: {iss}")
        
        elif self.config.tenant_id_source == "custom":
            # Extract from custom claim
            tenant_id = payload.get(self.config.tenant_id_claim)
            if not tenant_id:
                raise TokenInvalidError(
                    f"Custom tenant_id claim '{self.config.tenant_id_claim}' not found"
                )
            return str(tenant_id)
        
        elif self.config.tenant_id_source == "fixed":
            # Use fixed value
            return self.config.tenant_id_fixed
        
        raise TokenInvalidError(f"Invalid tenant_id_source: {self.config.tenant_id_source}")

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Create 401 unauthorized response."""
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": message
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    def _error_response(self, message: str, status_code: int = 500) -> JSONResponse:
        """Create error response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "internal_server_error" if status_code == 500 else "service_unavailable",
                "message": message
            }
        )
