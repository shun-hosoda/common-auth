"""Setup function for FastAPI application."""

import logging
import os
from typing import Optional

from fastapi import FastAPI
from common_auth.config import AuthConfig
from common_auth.middleware.security_headers import SecurityHeadersMiddleware
from common_auth.middleware.jwt_auth import JWTAuthMiddleware
from common_auth.middleware.tenant import TenantMiddleware
from common_auth.middleware.rate_limit import RateLimitMiddleware, RateLimitStore
from common_auth.routers.auth import router as auth_router
from common_auth.routers.admin import router as admin_router
from common_auth.routers.audit import router as audit_router
from common_auth.routers.groups import router as groups_router
from common_auth.routers.invitation import router as invitation_router
from common_auth.services.email_service import EmailService

logger = logging.getLogger(__name__)


def setup_auth(
    app: FastAPI,
    config: AuthConfig,
    *,
    rate_limit_store: RateLimitStore | None = None,
    db_dsn: Optional[str] = None,
) -> None:
    """
    Setup authentication for FastAPI application.

    This function:
    1. Adds security middleware (in correct order)
    2. Mounts authentication router
    3. Configures JWKS service
    4. Optionally initialises an asyncpg DB connection pool for group/permission APIs

    Args:
        app: FastAPI application instance
        config: Authentication configuration
        rate_limit_store: Optional custom RateLimitStore implementation
        db_dsn: Optional PostgreSQL DSN (e.g. from DATABASE_URL env var).
                When provided, a DBClient is created and stored in app.state.db
                and the /admin/groups and /admin/permissions routers are mounted.

    Example:
        ```python
        from fastapi import FastAPI
        from common_auth import AuthConfig, setup_auth
        import os

        app = FastAPI()
        config = AuthConfig.from_env()
        setup_auth(app, config, db_dsn=os.environ.get("DATABASE_URL"))
        ```
    """
    app.state.auth_config = config

    # EmailService — used by invitation router
    app.state.email_service = EmailService(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        from_addr=config.smtp_from,
        use_tls=config.smtp_use_tls,
        username=config.smtp_username,
        password=config.smtp_password,
    )

    # DB connection pool (optional — required for group/permission APIs)
    _resolved_dsn = db_dsn or os.environ.get("DATABASE_URL")
    if _resolved_dsn:
        from common_auth.services.db_client import DBClient

        @app.on_event("startup")
        async def _startup_db() -> None:
            app.state.db = await DBClient.create(_resolved_dsn)
            logger.info("DBClient pool created")

        @app.on_event("shutdown")
        async def _shutdown_db() -> None:
            if hasattr(app.state, "db"):
                await app.state.db.close()
                logger.info("DBClient pool closed")

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
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

    # Mount groups/permissions router (requires DB pool)
    if _resolved_dsn:
        app.include_router(groups_router, prefix="/api/admin", tags=["groups"])
        app.include_router(audit_router, prefix="/api/admin", tags=["audit"])

    # Mount invitation router (Public endpoints + admin invitation management)
    # /api/invitations/validate and /api/invitations/accept are JWT-excluded
    # Public endpoints; /api/admin/invitations/* require tenant_admin JWT.
    app.include_router(invitation_router, tags=["invitations"])
