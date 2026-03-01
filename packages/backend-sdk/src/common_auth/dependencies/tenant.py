"""Tenant-related dependencies."""

from fastapi import Request, HTTPException, status


async def get_tenant_id(request: Request) -> str:
    """
    Get tenant ID from request state.
    
    This dependency requires JWTAuthMiddleware to be installed.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tenant ID
        
    Raises:
        HTTPException: 401 if tenant ID is not available
        
    Example:
        ```python
        @app.get("/api/data")
        async def get_data(tenant_id: str = Depends(get_tenant_id)):
            return {"tenant": tenant_id}
        ```
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not available",
        )
    
    return tenant_id
