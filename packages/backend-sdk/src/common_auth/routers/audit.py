"""Audit log router — FT-003.

Provides read-only access to the audit_logs table for admin users.

Endpoints:
    GET /admin/audit/logs   — paginated audit log retrieval

Tenant resolution rules (all endpoints):
    - super_admin: ``tenant_id`` query param is **required** (HTTP 400 if omitted)
    - tenant_admin: ``tenant_id`` query param is optional; JWT tenant_id is used
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
from common_auth.services.audit_service import AuditService
from common_auth.services.db_client import DBClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_admin(user: AuthUser) -> None:
    """Raise 403 unless caller has tenant_admin or super_admin."""
    if not ({"tenant_admin", "super_admin"} & set(user.roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_admin or super_admin role required",
        )


def _resolve_tenant(user: AuthUser, tenant_id: str | None) -> str:
    """Resolve target tenant ID from caller role and explicit query param.

    super_admin: *tenant_id* query param is required (HTTP 400 if absent).
    tenant_admin: uses JWT tenant_id; explicit *tenant_id* is ignored.
    """
    if "super_admin" in user.roles:
        if tenant_id:
            return tenant_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="super_admin must specify tenant_id",
        )
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id not found in token",
        )
    return user.tenant_id


def _get_audit_service(request: Request) -> AuditService:
    if not hasattr(request.app.state, "db"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit API requires DATABASE_URL to be configured",
        )
    db: DBClient = request.app.state.db
    return AuditService(db)


# ── Response models ───────────────────────────────────────────────────────────


class AuditLogEntry(BaseModel):
    id: str
    tenant_id: str
    actor_id: str | None
    actor_email: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict
    ip_address: str | None
    user_agent: str | None
    created_at: str


class AuditLogsResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int
    page: int
    per_page: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/audit/logs", response_model=AuditLogsResponse, tags=["audit"])
async def list_audit_logs(
    request: Request,
    tenant_id: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    page: int = 1,
    per_page: int = 50,
    user: AuthUser = Depends(get_current_user),
) -> AuditLogsResponse:
    """Return paginated audit log entries for the resolved tenant.

    Query parameters:
        tenant_id: Required for super_admin; ignored for tenant_admin.
        action:    Filter by action prefix. Supports trailing ``*`` wildcard
                   (e.g. ``group.*`` matches all group actions).
        actor_id:  Filter by actor UUID.
        from_dt:   ISO-8601 lower bound for ``created_at`` (inclusive).
        to_dt:     ISO-8601 upper bound for ``created_at`` (inclusive).
        page:      1-based page number (default: 1).
        per_page:  Records per page, max 200 (default: 50).
    """
    _require_admin(user)
    resolved_tenant_id = _resolve_tenant(user, tenant_id)

    svc = _get_audit_service(request)
    logs, total = await svc.list_logs(
        tenant_id=resolved_tenant_id,
        action_prefix=action,
        actor_id=actor_id,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        per_page=per_page,
        is_super_admin="super_admin" in user.roles,
    )

    return AuditLogsResponse(
        logs=[AuditLogEntry(**entry) for entry in logs],
        total=total,
        page=page,
        per_page=per_page,
    )
