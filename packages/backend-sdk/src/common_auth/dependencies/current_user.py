"""Dependency functions for FastAPI."""

from fastapi import Request, HTTPException, status
from common_auth.models.auth_user import AuthUser


async def get_current_user(request: Request) -> AuthUser:
    """
    Get currently authenticated user from request state.
    
    This dependency requires JWTAuthMiddleware to be installed.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: 401 if user is not authenticated
        
    Example:
        ```python
        @app.get("/api/protected")
        async def protected(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.sub}
        ```
    """
    user = getattr(request.state, "user", None)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_optional_user(request: Request) -> AuthUser | None:
    """
    Get currently authenticated user if available, otherwise None.
    
    This dependency is useful for endpoints that work for both
    authenticated and anonymous users.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Authenticated user or None
        
    Example:
        ```python
        @app.get("/api/public")
        async def public(user: AuthUser | None = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous"}
        ```
    """
    return getattr(request.state, "user", None)
