"""Example FastAPI application using common-auth."""

# ── Load .env BEFORE any imports that read os.environ ─────────────────────────
from dotenv import load_dotenv  # noqa: E402  isort:skip
load_dotenv()
# ──────────────────────────────────────────────────────────────────────────────

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

import asyncpg

from common_auth import AuthConfig, setup_auth, get_current_user, get_optional_user, AuthUser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting example FastAPI app with common-auth")

    # ── App DB connection pool (optional) ──
    db_url = os.environ.get("APP_DATABASE_URL")
    if db_url:
        try:
            app.state.db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
            logger.info(f"App DB pool created: {db_url.split('@')[-1]}")
        except Exception as e:
            logger.warning(f"App DB connection failed (user-groups endpoint disabled): {e}")
            app.state.db_pool = None
    else:
        app.state.db_pool = None
        logger.info("APP_DATABASE_URL not set — user-groups endpoint disabled")

    yield

    if getattr(app.state, "db_pool", None):
        await app.state.db_pool.close()
    logger.info("Shutting down example FastAPI app")


# Create FastAPI app
app = FastAPI(
    title="Common Auth Example",
    description="Example application demonstrating common-auth usage",
    version="1.0.0",
    lifespan=lifespan
)

# Setup authentication
try:
    config = AuthConfig.from_env()
    setup_auth(app, config)
    logger.info(f"Authentication configured for realm: {config.keycloak_realm}")
except Exception as e:
    logger.error(f"Failed to configure authentication: {e}")
    raise


# Public endpoint (no authentication required)
@app.get("/")
async def root():
    """Public root endpoint."""
    return {
        "message": "Welcome to Common Auth Example",
        "docs": "/docs",
        "auth_health": "/auth/health"
    }


# Public endpoint with optional authentication
@app.get("/api/public")
async def public_endpoint(user: AuthUser | None = Depends(get_optional_user)):
    """Public endpoint that works for both authenticated and anonymous users."""
    if user:
        return {
            "message": f"Hello {user.email}!",
            "authenticated": True,
            "user_id": user.sub
        }
    return {
        "message": "Hello anonymous user!",
        "authenticated": False
    }


# Protected endpoint (authentication required)
@app.get("/api/protected")
async def protected_endpoint(user: AuthUser = Depends(get_current_user)):
    """Protected endpoint requiring authentication."""
    return {
        "message": "Access granted to protected resource",
        "user": {
            "id": user.sub,
            "email": user.email,
            "tenant": user.tenant_id,
            "roles": user.roles
        }
    }


# Admin endpoint (authentication + role check)
@app.get("/api/admin")
async def admin_endpoint(user: AuthUser = Depends(get_current_user)):
    """Admin endpoint requiring 'admin' role."""
    if not user.has_role("admin"):
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "message": "Admin role required"}
        )
    
    return {
        "message": "Admin access granted",
        "user": {
            "id": user.sub,
            "email": user.email,
            "roles": user.roles
        }
    }


# ────────────────────────────────────────────────────────────────────────────
# User-with-groups endpoint (queries app DB)
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/admin/users-with-groups")
async def list_users_with_groups(user: AuthUser = Depends(get_current_user)):
    """List users from app DB enriched with tenant group memberships."""
    if not user.has_role("tenant_admin") and not user.has_role("super_admin"):
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "message": "Admin role required"}
        )

    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "message": "App DB not configured"}
        )

    is_super = user.has_role("super_admin")

    query = """
        SELECT
            up.id::text        AS id,
            up.email,
            up.display_name,
            up.roles,
            up.is_active,
            up.job_title,
            up.last_login_at,
            up.created_at,
            t.realm_name        AS tenant_id,
            COALESCE(
                array_agg(DISTINCT tg.name) FILTER (WHERE tg.name IS NOT NULL),
                ARRAY[]::text[]
            )                   AS groups
        FROM user_profiles up
        JOIN tenants t ON t.id = up.tenant_id
        LEFT JOIN user_group_memberships ugm ON ugm.user_id = up.id
        LEFT JOIN tenant_groups tg ON tg.id = ugm.group_id AND tg.is_active = TRUE
    """
    params: list = []
    if not is_super:
        query += " WHERE t.realm_name = $1"
        params.append(user.tenant_id)

    query += (
        " GROUP BY up.id, up.email, up.display_name, up.roles,"
        " up.is_active, up.job_title, up.last_login_at, up.created_at, t.realm_name"
        " ORDER BY up.created_at DESC"
    )

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception as e:
        logger.error(f"DB query failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "message": "Database query failed"}
        )

    return [
        {
            "id": r["id"],
            "email": r["email"],
            "displayName": r["display_name"],
            "roles": list(r["roles"]) if r["roles"] else [],
            "enabled": r["is_active"],
            "jobTitle": r["job_title"],
            "lastLoginAt": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            "tenantId": r["tenant_id"],
            "groups": list(r["groups"]),
        }
        for r in rows
    ]


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
