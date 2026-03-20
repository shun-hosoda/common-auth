"""Example FastAPI application using common-auth."""

# ── Load .env BEFORE any imports that read os.environ ─────────────────────────
from dotenv import load_dotenv  # noqa: E402  isort:skip
load_dotenv()
# ──────────────────────────────────────────────────────────────────────────────

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

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
    yield
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
