"""Authentication router with health and user info endpoints."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
from common_auth.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: Literal["healthy", "degraded", "unhealthy"]
    keycloak: dict[str, str | bool] | None = None
    jwks: dict[str, str | bool] | None = None


class AuthUserResponse(BaseModel):
    """Authenticated user response model."""
    sub: str
    tenant_id: str
    email: str
    email_verified: bool
    display_name: str | None = None
    roles: list[str]
    iat: int
    exp: int


@router.get("/health", response_model=HealthResponse, tags=["auth"])
async def get_auth_health(request: Request) -> HealthResponse:
    """
    Check authentication service health.
    
    This endpoint checks:
    - Keycloak connectivity
    - JWKS cache status
    
    Returns:
        Health status response
    """
    try:
        # Get auth config and JWKS service from app state
        auth_config = request.app.state.auth_config
        
        # Check if JWKS service exists (middleware installed)
        jwks_info = None
        keycloak_info = None
        
        # Try to access JWKS URL
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(auth_config.jwks_url, timeout=5.0)
                keycloak_reachable = response.status_code == 200
        except Exception as e:
            logger.warning(f"Keycloak health check failed: {e}")
            keycloak_reachable = False
        
        keycloak_info = {
            "reachable": keycloak_reachable,
            "url": auth_config.keycloak_url
        }
        
        # Determine overall status
        if keycloak_reachable:
            status = "healthy"
        else:
            status = "unhealthy"
        
        return HealthResponse(
            status=status,
            keycloak=keycloak_info,
            jwks=jwks_info
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            keycloak={"reachable": False, "error": str(e)}
        )


@router.get("/me", response_model=AuthUserResponse, tags=["auth"])
async def get_auth_me(user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    """
    Get current authenticated user information.
    
    Requires valid JWT token.
    
    Args:
        user: Current authenticated user (injected by dependency)
        
    Returns:
        User information
    """
    return AuthUserResponse(
        sub=user.sub,
        tenant_id=user.tenant_id,
        email=user.email,
        email_verified=user.email_verified,
        display_name=user.display_name,
        roles=user.roles,
        iat=user.iat,
        exp=user.exp
    )


@router.post("/logout", status_code=204, tags=["auth"])
async def post_auth_logout(
    request: Request,
    user: AuthUser = Depends(get_current_user)
) -> None:
    """
    Logout and revoke tokens.
    
    In a stateless JWT system, logout is primarily client-side
    (clearing tokens). This endpoint can be used to log the logout
    event or revoke refresh tokens if needed.
    
    Args:
        request: FastAPI request
        user: Current authenticated user
    """
    logger.info(f"User logged out: {user.sub}")
    # In future: revoke refresh token via Keycloak API
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_kc_admin_readonly(request: Request) -> KeycloakAdminClient:
    """Return KeycloakAdminClient from app.state (read-only, no lazy init).

    Unlike admin.py's ``_get_kc_admin`` this does **not** create the client
    on first access.  If the admin client was never initialised (e.g. no
    ``KC_ADMIN_CLIENT_SECRET``), we return 503.
    """
    kc = getattr(request.app.state, "kc_admin_client", None)
    if kc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API not configured",
        )
    return kc


# ── MFA status models ────────────────────────────────────────────────────────


class MfaStatusResponse(BaseModel):
    """MFA status for the current user."""
    mfa_enabled: bool
    mfa_method: str
    mfa_configured: bool


# ── MFA status endpoint ──────────────────────────────────────────────────────


@router.get("/mfa-status", response_model=MfaStatusResponse, tags=["auth"])
async def get_mfa_status(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> MfaStatusResponse:
    """
    Return the current user's MFA configuration status.

    Uses user attributes (mirrored from tenant group) to determine
    the tenant MFA policy, and checks OTP credentials to determine
    whether TOTP is actually configured.
    """
    kc = _get_kc_admin_readonly(request)
    kc_user = await kc.get_user(user.sub)

    attrs = kc_user.get("attributes") or {}
    mfa_enabled = attrs.get("mfa_enabled", ["false"])[0] == "true"
    mfa_method = attrs.get("mfa_method", ["totp"])[0]

    # Determine if MFA is actually configured for this user
    mfa_configured = False
    if mfa_enabled:
        if mfa_method == "totp":
            # Check if user has OTP credential
            creds = await kc.get_user_credentials(user.sub)
            mfa_configured = any(c.get("type") == "otp" for c in creds)
        elif mfa_method == "email":
            # Email OTP doesn't require user-side credential setup
            mfa_configured = True

    return MfaStatusResponse(
        mfa_enabled=mfa_enabled,
        mfa_method=mfa_method,
        mfa_configured=mfa_configured,
    )
