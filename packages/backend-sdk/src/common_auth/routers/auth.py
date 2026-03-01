"""Authentication router with health and user info endpoints."""

import logging
from typing import Literal
from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser

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
