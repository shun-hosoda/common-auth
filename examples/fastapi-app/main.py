"""Example FastAPI application using common-auth."""

# ── Load .env BEFORE any imports that read os.environ ─────────────────────────
from pathlib import Path  # noqa: E402  isort:skip
from dotenv import load_dotenv  # noqa: E402  isort:skip
load_dotenv(Path(__file__).resolve().parent / ".env")
# ──────────────────────────────────────────────────────────────────────────────

import logging
import asyncio
import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import asyncpg

from common_auth import AuthConfig, setup_auth, get_current_user, get_optional_user, AuthUser
from common_auth.services.keycloak_admin_client import KeycloakAdminClient
from common_auth.services.db_client import DBClient

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
        connect_kwargs: dict = {}
        # Windows + Docker Desktop での瞬断対策: ローカルPostgresは SSL を明示的に無効化
        if "localhost" in db_url or "127.0.0.1" in db_url:
            connect_kwargs["ssl"] = False

        pool: asyncpg.Pool | None = None
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                pool = await asyncpg.create_pool(
                    db_url,
                    min_size=2,
                    max_size=10,
                    **connect_kwargs,
                )
                break
            except Exception as e:
                last_error = e
                if attempt < 3:
                    logger.warning(
                        "App DB connect attempt %s/3 failed: %s (retrying)",
                        attempt,
                        e,
                    )
                    await asyncio.sleep(1.5 * attempt)

        if pool is not None:
            app.state.db_pool = pool
            logger.info(f"App DB pool created: {db_url.split('@')[-1]}")
            # DBClient for groups/audit routers (uses app.state.db)
            app.state.db = await DBClient.create(db_url)
            logger.info("DBClient pool created for admin routers")
        else:
            logger.warning(
                "App DB connection failed after retries (user-groups endpoint disabled): %s",
                last_error,
            )
            app.state.db_pool = None
    else:
        app.state.db_pool = None
        logger.info("APP_DATABASE_URL not set — user-groups endpoint disabled")

    # ── Keycloak Admin Client (required for /auth/mfa-status etc.) ──
    admin_client_id = os.environ.get("KC_ADMIN_CLIENT_ID", "admin-api-client")
    admin_client_secret = os.environ.get("KC_ADMIN_CLIENT_SECRET", "")
    if admin_client_secret:
        auth_cfg = app.state.auth_config
        app.state.kc_admin_client = KeycloakAdminClient(
            keycloak_url=auth_cfg.keycloak_url,
            realm=auth_cfg.keycloak_realm,
            client_id=admin_client_id,
            client_secret=admin_client_secret,
        )
        logger.info("Keycloak admin client initialized (client_id=%s)", admin_client_id)
    else:
        logger.warning("KC_ADMIN_CLIENT_SECRET not set — Admin API endpoints will return 503")

    yield

    if getattr(app.state, "db_pool", None):
        await app.state.db_pool.close()
    if getattr(app.state, "db", None):
        await app.state.db.close()
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
    setup_auth(app, config, db_dsn=os.environ.get("APP_DATABASE_URL"))
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


# ────────────────────────────────────────────────────────────────────────────
# Change password endpoint (via Keycloak Admin API)
# ────────────────────────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


@app.put("/api/users/me/password")
async def change_my_password(
    body: ChangePasswordRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Change the authenticated user's password.

    1. Verify the current password via ROPC grant (so we validate before mutating).
    2. Update the password through the Keycloak Admin REST API.
    """
    kc_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.environ.get("KEYCLOAK_REALM", "common-auth")
    frontend_client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "example-app")
    admin_client_id = os.environ.get("KC_ADMIN_CLIENT_ID", "admin-api-client")
    admin_client_secret = os.environ.get("KC_ADMIN_CLIENT_SECRET", "")

    if body.currentPassword == body.newPassword:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_password", "message": "新しいパスワードは現在のパスワードと異なる値にしてください"},
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # ── Step 1: Verify current password via ROPC ───────────────────────
        verify_resp = await client.post(
            f"{kc_url}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": frontend_client_id,
                "username": user.email,
                "password": body.currentPassword,
            },
        )
        if verify_resp.status_code != 200:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_current_password", "message": "現在のパスワードが正しくありません"},
            )

        # ── Step 2: Obtain admin token ─────────────────────────────────────
        if not admin_client_secret:
            logger.error("KC_ADMIN_CLIENT_SECRET is not set")
            return JSONResponse(
                status_code=503,
                content={"error": "not_configured", "message": "Admin API not configured"},
            )

        token_resp = await client.post(
            f"{kc_url}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": admin_client_id,
                "client_secret": admin_client_secret,
            },
        )
        if token_resp.status_code != 200:
            logger.error("Admin token request failed: %s", token_resp.text)
            return JSONResponse(
                status_code=503,
                content={"error": "admin_token_failed", "message": "管理トークンの取得に失敗しました"},
            )

        admin_token = token_resp.json()["access_token"]

        # ── Step 3: Update password via Admin API ──────────────────────────
        update_resp = await client.put(
            f"{kc_url}/admin/realms/{realm}/users/{user.sub}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"type": "password", "value": body.newPassword, "temporary": False},
        )

        if update_resp.status_code not in (200, 204):
            error_text = update_resp.text
            logger.error("Password update failed [%s]: %s", update_resp.status_code, error_text)
            try:
                detail = update_resp.json().get("errorMessage", "パスワードの変更に失敗しました")
            except Exception:
                detail = "パスワードの変更に失敗しました"
            return JSONResponse(
                status_code=400,
                content={"error": "update_failed", "message": detail},
            )

    logger.info("Password changed for user %s", user.sub)
    return Response(status_code=204)


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
