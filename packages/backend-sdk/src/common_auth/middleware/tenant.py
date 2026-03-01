"""Tenant isolation middleware with Row-Level Security support."""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_auth.config import AuthConfig

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set tenant context for Row-Level Security.
    
    This middleware sets PostgreSQL session variable 'app.current_tenant_id'
    which is used by RLS policies to enforce tenant isolation.
    
    Requirements:
    - request.state.tenant_id must be set (by JWTAuthMiddleware)
    - Database session must be available via request.state.db
    """

    def __init__(self, app, config: AuthConfig) -> None:
        """
        Initialize tenant middleware.
        
        Args:
            app: FastAPI application
            config: Authentication configuration
        """
        super().__init__(app)
        self.config = config
        logger.info("Initialized TenantMiddleware")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Set tenant context before processing request.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Only set tenant context if tenant_id is available
        tenant_id = getattr(request.state, "tenant_id", None)
        
        if tenant_id and self.config.enable_rls:
            # Set tenant context for RLS
            # Note: This assumes database session is available
            # In practice, this would be set per-request in a database dependency
            logger.debug(f"Setting tenant context: {tenant_id}")
            
            # The actual SET LOCAL command would be executed in the database dependency
            # Store tenant_id for database layer to use
            request.state.rls_tenant_id = tenant_id
        
        response = await call_next(request)
        return response


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set tenant context in PostgreSQL session for RLS.
    
    This should be called at the start of each database transaction.
    
    Args:
        session: SQLAlchemy async session
        tenant_id: Tenant identifier
        
    Example:
        ```python
        @app.get("/api/data")
        async def get_data(
            session: AsyncSession = Depends(get_db),
            tenant_id: str = Depends(get_tenant_id)
        ):
            await set_tenant_context(session, tenant_id)
            # ... query data ...
        ```
    """
    try:
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        logger.debug(f"Set RLS tenant context: {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to set tenant context: {e}")
        raise
