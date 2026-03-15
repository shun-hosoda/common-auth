"""Setup function for FastAPI application."""

from fastapi import FastAPI
from common_auth.config import AuthConfig
from common_auth.middleware.security_headers import SecurityHeadersMiddleware
from common_auth.middleware.jwt_auth import JWTAuthMiddleware
from common_auth.middleware.tenant import TenantMiddleware
from common_auth.middleware.rate_limit import RateLimitMiddleware, RateLimitStore
from common_auth.routers.auth import router as auth_router
from common_auth.routers.admin import router as admin_router


def setup_auth(
    app: FastAPI,
    config: AuthConfig,
    *,
    rate_limit_store: RateLimitStore | None = None,
) -> None:
    """
    Setup authentication for FastAPI application.
    
    This function:
    1. Adds security middleware (in correct order)
    2. Mounts authentication router
    3. Configures JWKS service
    
    Args:
        app: FastAPI application instance
        config: Authentication configuration
        rate_limit_store: Optional custom RateLimitStore implementation
        
    Example:
        ```python
        from fastapi import FastAPI
        from common_auth import AuthConfig, setup_auth
        
        app = FastAPI()
        config = AuthConfig.from_env()
        setup_auth(app, config)
        ```
    """
    app.state.auth_config = config
    
    # Middleware execution order: SecurityHeaders -> RateLimit -> JWTAuth -> Tenant
    # Added in reverse order because Starlette executes them LIFO.
    
    # 4. Tenant middleware (innermost)
    if config.enable_rls:
        app.add_middleware(TenantMiddleware, config=config)
    
    # 3. JWT authentication middleware
    app.add_middleware(JWTAuthMiddleware, config=config)
    
    # 2. Rate limiting middleware
    if config.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            config=config,
            store=rate_limit_store,
        )
    
    # 1. Security headers middleware (outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Mount authentication router
    app.include_router(auth_router, prefix="/auth", tags=["auth"])

    # Mount admin router (lazy — KeycloakAdminClient is created on first use)
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
