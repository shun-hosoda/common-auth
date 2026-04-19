"""Admin router — user management and client (tenant) management.

All endpoints require ``tenant_admin`` or ``super_admin`` role (verified
from the caller's JWT by the upstream JWTAuthMiddleware).

Keycloak Admin REST API is called internally using the
``KeycloakAdminClient`` service account (client_credentials); the
caller's JWT is never forwarded to Keycloak Admin API.

Environment variables required:
    KC_ADMIN_CLIENT_ID:     Keycloak client ID for service account
                            (default: "admin-api-client")
    KC_ADMIN_CLIENT_SECRET: Keycloak client secret for service account
"""

import asyncio
import os
import logging
import uuid
from typing import cast
from typing import Any, Literal

import httpx

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
from common_auth.models.group import BulkPermissionUpdateRequest
from common_auth.services.group_service import GroupService
from common_auth.services.permission_service import PermissionService
from common_auth.services.audit_service import AuditService, AuditEntry
from common_auth.services.db_client import DBClient
from common_auth.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_kc_admin(request: Request) -> KeycloakAdminClient:
    """Return cached KeycloakAdminClient, creating it on first call."""
    if not hasattr(request.app.state, "kc_admin_client"):
        config = request.app.state.auth_config
        client_id = os.environ.get("KC_ADMIN_CLIENT_ID", "admin-api-client")
        client_secret = os.environ.get("KC_ADMIN_CLIENT_SECRET", "")
        if not client_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin API not configured (KC_ADMIN_CLIENT_SECRET missing)",
            )
        request.app.state.kc_admin_client = KeycloakAdminClient(
            keycloak_url=config.keycloak_url,
            realm=config.keycloak_realm,
            client_id=client_id,
            client_secret=client_secret,
        )
    return cast(KeycloakAdminClient, request.app.state.kc_admin_client)


def _require_admin(user: AuthUser) -> None:
    """Raise 403 unless caller has tenant_admin or super_admin."""
    if not ({"tenant_admin", "super_admin"} & set(user.roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_admin or super_admin role required",
        )


def _require_super_admin(user: AuthUser) -> None:
    """Raise 403 unless caller has super_admin."""
    if "super_admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="super_admin role required",
        )


def _tenant_filter(user: AuthUser) -> str | None:
    """Return tenant_id to filter by, or None for super_admin (unrestricted)."""
    return None if "super_admin" in user.roles else user.tenant_id


async def _check_tenant_boundary(
    kc: KeycloakAdminClient,
    user_id: str,
    caller: AuthUser,
) -> dict[str, Any]:
    """Fetch target user and raise 403 if caller is outside its tenant."""
    target = await kc.get_user(user_id)
    if "super_admin" not in caller.roles:
        target_tenants: list[str] = (
            target.get("attributes") or {}
        ).get("tenant_id", [])
        if caller.tenant_id not in target_tenants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: target user belongs to a different tenant",
            )
    return target


# ── Request / Response models ─────────────────────────────────────────────────


class CreateUserBody(BaseModel):
    email: str
    firstName: str = ""
    lastName: str = ""
    password: str
    temporary: bool = True


class UpdateUserBody(BaseModel):
    email: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    enabled: bool | None = None


class ResetPasswordBody(BaseModel):
    newPassword: str
    temporary: bool = True


class CreateClientBody(BaseModel):
    clientId: str
    name: str = ""
    description: str = ""


class MfaSettingsBody(BaseModel):
    mfa_enabled: bool
    mfa_method: Literal["totp", "email"] = "totp"


class AddUserToGroupBody(BaseModel):
    group_id: uuid.UUID


# ── User endpoints ────────────────────────────────────────────────────────────


@router.get("/users", tags=["admin"])
async def list_users(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    List users in caller's tenant (all tenants for super_admin).

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    return await kc.list_users(tenant_id=_tenant_filter(user))


@router.post("/users", status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_user(
    body: CreateUserBody,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Create a new user in the caller's tenant.

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    kc = _get_kc_admin(request)

    payload: dict[str, Any] = {
        "username": body.email,
        "email": body.email,
        "firstName": body.firstName,
        "lastName": body.lastName,
        "enabled": True,
        "emailVerified": True,
        "attributes": {"tenant_id": [user.tenant_id]},
        "credentials": [
            {
                "type": "password",
                "value": body.password,
                "temporary": body.temporary,
            }
        ],
    }

    try:
        new_id = await kc.create_user(payload)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Keycloak error: {exc.response.status_code}",
        ) from exc

    # Add to tenant group and assign default role in parallel (best-effort)
    if new_id:
        group = await kc.find_group_by_name(user.tenant_id)
        await asyncio.gather(
            kc.add_user_to_group(new_id, group["id"]) if group else asyncio.sleep(0),
            kc.assign_realm_role(new_id, "user"),
            return_exceptions=True,  # best-effort: don't fail on role/group errors
        )

        # ── MFA extension: set MFA attrs for new user if tenant MFA is enabled ──
        if group:
            try:
                full_group = await kc.get_group(group["id"])
                group_attrs = full_group.get("attributes") or {}
                mfa_enabled = group_attrs.get("mfa_enabled", ["false"])[0]
                mfa_method = group_attrs.get("mfa_method", ["totp"])[0]
                if mfa_enabled == "true":
                    # totp: CONFIGURE_TOTP を必須アクションとして付与
                    # email: 認証コードをメールで受け取るだけなので required action は不要
                    required_actions = ["CONFIGURE_TOTP"] if mfa_method == "totp" else []
                    await kc.update_user(new_id, {
                        "attributes": {
                            "tenant_id": [user.tenant_id],
                            "mfa_enabled": ["true"],
                            "mfa_method": [mfa_method],
                        },
                        "requiredActions": required_actions,
                    })
            except Exception:
                logger.warning(
                    "Failed to set MFA attributes for new user %s (best-effort)",
                    new_id,
                    exc_info=True,
                )

    return {"id": new_id}


@router.get("/users/{user_id}", tags=["admin"])
async def get_user(
    user_id: str,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get user details.

    Requires: tenant_admin or super_admin (own tenant only for tenant_admin)
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    return await _check_tenant_boundary(kc, user_id, user)


@router.put("/users/{user_id}", tags=["admin"])
async def update_user(
    user_id: str,
    body: UpdateUserBody,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Update user information.

    Requires: tenant_admin or super_admin (own tenant only for tenant_admin)
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    await _check_tenant_boundary(kc, user_id, user)

    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    await kc.update_user(user_id, payload)
    return {"status": "updated"}


@router.delete("/users/{user_id}", tags=["admin"])
async def disable_user(
    user_id: str,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Logically delete (disable) a user.

    Requires: tenant_admin or super_admin (own tenant only for tenant_admin)
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    target = await _check_tenant_boundary(kc, user_id, user)

    if target.get("id") == user.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )

    await kc.disable_user(user_id)
    return {"status": "disabled"}


@router.post("/users/{user_id}/reset-password", tags=["admin"])
async def reset_password(
    user_id: str,
    body: ResetPasswordBody,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Reset a user's password.

    Requires: tenant_admin or super_admin (own tenant only for tenant_admin)
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    await _check_tenant_boundary(kc, user_id, user)
    await kc.reset_password(user_id, body.newPassword, body.temporary)
    return {"status": "password_reset"}


@router.post("/users/{user_id}/reset-mfa", tags=["admin"])
async def reset_mfa(
    user_id: str,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Remove all TOTP credentials (MFA reset) for a user.

    Requires: tenant_admin or super_admin (own tenant only for tenant_admin)
    """
    _require_admin(user)
    kc = _get_kc_admin(request)
    await _check_tenant_boundary(kc, user_id, user)
    await kc.reset_mfa(user_id)
    return {"status": "mfa_reset"}


# ── MFA policy endpoints ─────────────────────────────────────────────────────

# Limits concurrency for bulk Keycloak calls (reset_mfa, set_user_attributes, etc.)
_MFA_SEMAPHORE = asyncio.Semaphore(10)


@router.get("/security/mfa", tags=["admin"])
async def get_mfa_settings(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get current tenant MFA policy from group attributes.

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    kc = _get_kc_admin(request)

    group = await kc.find_group_by_name(user.tenant_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant group not found",
        )

    full_group = await kc.get_group(group["id"])
    attrs = full_group.get("attributes") or {}
    mfa_enabled = attrs.get("mfa_enabled", ["false"])[0] == "true"
    mfa_method = attrs.get("mfa_method", ["totp"])[0]

    return {"mfa_enabled": mfa_enabled, "mfa_method": mfa_method}


@router.put("/security/mfa", tags=["admin"])
async def update_mfa_settings(
    body: MfaSettingsBody,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Update tenant MFA policy and propagate to all tenant users.

    Flow:
    1. Permission check
    2. Find tenant group → get full group (2-stage for attributes)
    3. Update group attributes
    4. List all tenant users
    5. If method changed & MFA still enabled → bulk reset OTP credentials
    6. Set user attributes + required actions per final state
    7. Return update summary

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    kc = _get_kc_admin(request)

    # ── 2. Find group + get old attributes ────────────────────────────────
    group = await kc.find_group_by_name(user.tenant_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant group not found",
        )
    full_group = await kc.get_group(group["id"])
    old_attrs = full_group.get("attributes") or {}
    old_method = old_attrs.get("mfa_method", ["totp"])[0]

    new_enabled = body.mfa_enabled
    new_method = body.mfa_method

    # ── 3. Update group attributes ────────────────────────────────────────
    await kc.update_group_attributes(
        group["id"],
        {
            "mfa_enabled": [str(new_enabled).lower()],
            "mfa_method": [new_method],
        },
    )

    # ── 4. List all tenant users ──────────────────────────────────────────
    users = await kc.list_users(tenant_id=user.tenant_id)
    user_ids = [u["id"] for u in users]

    # ── 5. Method change → bulk reset MFA credentials ─────────────────────
    method_changed = old_method != new_method and new_enabled
    reset_failed: list[str] = []
    if method_changed:

        async def _reset_one(uid: str) -> None:
            async with _MFA_SEMAPHORE:
                await kc.reset_mfa(uid)

        results = await asyncio.gather(
            *[_reset_one(uid) for uid in user_ids],
            return_exceptions=True,
        )
        for uid, result in zip(user_ids, results):
            if isinstance(result, BaseException):
                logger.warning("reset_mfa failed for user %s: %s", uid, result)
                reset_failed.append(uid)

    # ── 6. Set user attributes + required actions ─────────────────────────
    user_attrs: dict[str, list[str]] = {
        "mfa_enabled": [str(new_enabled).lower()],
        "mfa_method": [new_method],
    }
    failed_attr = await kc.set_user_attributes_bulk(user_ids, user_attrs)

    if new_enabled and new_method == "totp":
        failed_action = await kc.add_required_action_bulk(user_ids, "CONFIGURE_TOTP")
        # Email OTP setup action no longer needed — remove if present
        await kc.remove_required_action_bulk(user_ids, "email-authenticator-setup")
        failed_action = failed_action  # keep TOTP failures
    elif new_enabled and new_method == "email":
        # Email OTP: no credential setup needed — email is already registered.
        # Just remove TOTP required action; the auth flow handles OTP on next login.
        failed_action = await kc.remove_required_action_bulk(user_ids, "CONFIGURE_TOTP")
        await kc.remove_required_action_bulk(user_ids, "email-authenticator-setup")
    else:
        # MFA disabled → remove both
        failed_action = await kc.remove_required_action_bulk(user_ids, "CONFIGURE_TOTP")
        await kc.remove_required_action_bulk(user_ids, "email-authenticator-setup")

    # ── 7. Invalidate active sessions for all affected users ──────────────
    # When MFA is enabled or method changes, force re-authentication so users
    # must go through the full Keycloak authentication flow (including MFA gate)
    # on their next login. Without this, users with active sessions bypass MFA.
    if new_enabled or method_changed:
        async def _logout_one(uid: str) -> None:
            async with _MFA_SEMAPHORE:
                await kc.logout_user(uid)

        await asyncio.gather(
            *[_logout_one(uid) for uid in user_ids],
            return_exceptions=True,   # ignore individual logout failures
        )

    # Merge failures (deduplicate)
    all_failed = list(set(failed_attr) | set(failed_action) | set(reset_failed))
    users_updated = len(user_ids) - len(all_failed)

    return {
        "status": "updated",
        "mfa_enabled": new_enabled,
        "mfa_method": new_method,
        "users_updated": users_updated,
        "users_failed": len(all_failed),
    }


# ── Client (tenant) endpoints ─────────────────────────────────────────────────


@router.get("/clients", tags=["admin"])
async def list_clients(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    List all tenants (Keycloak clients).

    Requires: super_admin
    """
    _require_super_admin(user)
    kc = _get_kc_admin(request)
    return await kc.list_clients()


@router.post("/clients", status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_client(
    body: CreateClientBody,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Register a new tenant (Keycloak client).

    Requires: super_admin
    """
    _require_super_admin(user)
    kc = _get_kc_admin(request)
    payload: dict[str, Any] = {
        "clientId": body.clientId,
        "name": body.name,
        "description": body.description,
        "publicClient": True,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "enabled": True,
    }
    new_id = await kc.create_client(payload)
    return {"id": new_id}


# ── User ↔ Group / Permission endpoints ──────────────────────────────────────
# These endpoints require the DB pool (app.state.db) to be initialised via
# setup_auth(..., db_dsn=...).


def _resolve_db_tenant(user: AuthUser, target_tenant: str | None = None) -> str:
    if "super_admin" in user.roles:
        if target_tenant:
            return target_tenant
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="super_admin must specify tenant_id for DB-backed endpoints",
        )

    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id not found in token",
        )
    return user.tenant_id


def _get_db_services(request: Request) -> tuple[GroupService, PermissionService]:
    """Return (GroupService, PermissionService) or raise 503 if DB not configured."""
    if not hasattr(request.app.state, "db"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Group/Permission API requires DATABASE_URL to be configured",
        )

    db: DBClient = request.app.state.db
    return GroupService(db), PermissionService(db)


@router.get("/users/{user_id}/groups", tags=["admin"])
async def list_user_groups(
    user_id: uuid.UUID,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    """Return all groups the target user belongs to."""
    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    group_svc, _ = _get_db_services(request)
    items = await group_svc.list_user_groups(
        tenant_id=resolved_tenant_id, user_id=user_id
    )
    return {"groups": items}


@router.post("/users/{user_id}/groups", status_code=204, tags=["admin"])
async def add_user_to_group(
    user_id: uuid.UUID,
    body: AddUserToGroupBody,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> None:
    """Add user to a group. Body: {group_id: uuid}"""
    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    group_id = body.group_id
    group_svc, _ = _get_db_services(request)
    await group_svc.add_user_to_group(
        tenant_id=resolved_tenant_id,
        user_id=user_id,
        group_id=group_id,
        added_by=uuid.UUID(user.sub),
    )


@router.delete("/users/{user_id}/groups/{group_id}", status_code=204, tags=["admin"])
async def remove_user_from_group(
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> None:
    """Remove user from a group."""
    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    group_svc, _ = _get_db_services(request)
    removed = await group_svc.remove_user_from_group(
        tenant_id=resolved_tenant_id, user_id=user_id, group_id=group_id
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )


@router.get("/users/{user_id}/permissions", tags=["admin"])
async def list_user_permissions(
    user_id: uuid.UUID,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    """Return effective permissions for a user (resolved group + direct)."""
    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    _, perm_svc = _get_db_services(request)
    items = await perm_svc.get_effective_permissions(
        tenant_id=resolved_tenant_id, user_id=user_id
    )
    return {"permissions": items}


@router.put("/users/{user_id}/permissions", status_code=204, tags=["admin"])
async def update_user_permissions(
    user_id: uuid.UUID,
    payload: BulkPermissionUpdateRequest,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> None:
    """Bulk-update user direct permission overrides."""
    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    _, perm_svc = _get_db_services(request)
    await perm_svc.update_user_permissions(
        tenant_id=resolved_tenant_id,
        user_id=user_id,
        updates=payload.permissions,
        granted_by=uuid.UUID(user.sub),
    )


# ─────────────────────────────────────────────────────────────────────────────
# FT-004  Password Policy
# FT-005  Session Settings
#
# Both operate against Keycloak Realm Settings (not DB-backed).
# Tenant resolution is used for access-control context and audit logging.
# In single-realm setups all tenants share one Keycloak realm.
# ─────────────────────────────────────────────────────────────────────────────


# ── Pydantic models ───────────────────────────────────────────────────────────

class PasswordPolicyResponse(BaseModel):
    min_length: int
    require_uppercase: bool
    require_digits: bool
    require_special: bool
    password_history: int
    expire_days: int


class PasswordPolicyRequest(BaseModel):
    min_length: int = 8
    require_uppercase: bool = True
    require_digits: bool = True
    require_special: bool = False
    password_history: int = 0
    expire_days: int = 0


class SessionSettingsResponse(BaseModel):
    access_token_lifespan: int
    sso_session_idle_timeout: int
    sso_session_max_lifespan: int


class SessionSettingsRequest(BaseModel):
    access_token_lifespan: int         # seconds: 60-3600
    sso_session_idle_timeout: int      # seconds: 300-86400
    sso_session_max_lifespan: int      # seconds: 300-7776000 (90 days)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_password_policy(policy_str: str) -> PasswordPolicyResponse:
    """Parse Keycloak passwordPolicy string into structured response.

    Keycloak stores password policy as a string like:
        "length(8) and upperCase(1) and digits(1) and passwordHistory(3)"
    """
    import re

    def _extract(pattern: str, default: int) -> int:
        m = re.search(pattern, policy_str)
        return int(m.group(1)) if m else default

    min_length = _extract(r"length\((\d+)\)", 8)
    uppercase_count = _extract(r"upperCase\((\d+)\)", 0)
    digits_count = _extract(r"digits\((\d+)\)", 0)
    special_count = _extract(r"specialChars\((\d+)\)", 0)
    history = _extract(r"passwordHistory\((\d+)\)", 0)
    expire_days = _extract(r"forceExpiredPasswordChange\((\d+)\)", 0)

    return PasswordPolicyResponse(
        min_length=min_length,
        require_uppercase=uppercase_count > 0,
        require_digits=digits_count > 0,
        require_special=special_count > 0,
        password_history=history,
        expire_days=expire_days,
    )


def _build_password_policy(req: PasswordPolicyRequest) -> str:
    """Build Keycloak passwordPolicy string from structured request."""
    parts = [f"length({req.min_length})"]
    if req.require_uppercase:
        parts.append("upperCase(1)")
    if req.require_digits:
        parts.append("digits(1)")
    if req.require_special:
        parts.append("specialChars(1)")
    if req.password_history > 0:
        parts.append(f"passwordHistory({req.password_history})")
    if req.expire_days > 0:
        parts.append(f"forceExpiredPasswordChange({req.expire_days})")
    return " and ".join(parts)


def _maybe_audit(
    request: Request,
    tenant_id: str,
    user: AuthUser,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget audit write if DB is configured, otherwise skip."""
    if not hasattr(request.app.state, "db"):
        return
    svc = AuditService(request.app.state.db)
    svc.log(
        tenant_id=tenant_id,
        actor_id=user.sub,
        actor_email=user.email,
        action=action,
        details=details or {},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/security/password-policy", response_model=PasswordPolicyResponse, tags=["security"])
async def get_password_policy(
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> PasswordPolicyResponse:
    """Return the current Keycloak password policy for the realm.

    Tenant resolution:
        - super_admin: ``tenant_id`` query param is required.
        - tenant_admin: ``tenant_id`` is optional; JWT tenant is used.
    """
    _require_admin(user)
    _resolve_db_tenant(user, tenant_id)  # enforces super_admin tenant_id rule
    kc = _get_kc_admin(request)
    realm = await kc.get_realm_settings()
    policy_str: str = realm.get("passwordPolicy", "")
    return _parse_password_policy(policy_str)


@router.put("/security/password-policy", response_model=PasswordPolicyResponse, tags=["security"])
async def update_password_policy(
    payload: PasswordPolicyRequest,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> PasswordPolicyResponse:
    """Update the Keycloak password policy for the realm.

    Validations:
        - min_length: 1-128
        - password_history: 0-24
        - expire_days: 0-365

    Tenant resolution:
        - super_admin: ``tenant_id`` query param is required.
        - tenant_admin: ``tenant_id`` is optional; JWT tenant is used.
    """
    if not (1 <= payload.min_length <= 128):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_length must be between 1 and 128",
        )
    if not (0 <= payload.password_history <= 24):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="password_history must be between 0 and 24",
        )
    if not (0 <= payload.expire_days <= 365):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expire_days must be between 0 and 365",
        )

    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    kc = _get_kc_admin(request)
    policy_str = _build_password_policy(payload)
    await kc.update_realm_settings({"passwordPolicy": policy_str})
    logger.info(
        "Password policy updated",
        extra={"tenant_id": resolved_tenant_id, "actor": user.email, "policy": policy_str},
    )
    _maybe_audit(
        request, resolved_tenant_id, user,
        "security.password_policy.update",
        {"policy": policy_str},
    )
    return _parse_password_policy(policy_str)


@router.get("/security/session", response_model=SessionSettingsResponse, tags=["security"])
async def get_session_settings(
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> SessionSettingsResponse:
    """Return the current Keycloak session timeout settings for the realm.

    Tenant resolution:
        - super_admin: ``tenant_id`` query param is required.
        - tenant_admin: ``tenant_id`` is optional; JWT tenant is used.
    """
    _require_admin(user)
    _resolve_db_tenant(user, tenant_id)
    kc = _get_kc_admin(request)
    realm = await kc.get_realm_settings()
    return SessionSettingsResponse(
        access_token_lifespan=realm.get("accessTokenLifespan", 300),
        sso_session_idle_timeout=realm.get("ssoSessionIdleTimeout", 1800),
        sso_session_max_lifespan=realm.get("ssoSessionMaxLifespan", 36000),
    )


@router.put("/security/session", response_model=SessionSettingsResponse, tags=["security"])
async def update_session_settings(
    payload: SessionSettingsRequest,
    request: Request,
    tenant_id: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> SessionSettingsResponse:
    """Update the Keycloak session timeout settings for the realm.

    Validations:
        - access_token_lifespan: 60-3600 seconds
        - sso_session_idle_timeout: 300-86400 seconds
        - sso_session_max_lifespan: 300-7776000 seconds (up to 90 days)

    Tenant resolution:
        - super_admin: ``tenant_id`` query param is required.
        - tenant_admin: ``tenant_id`` is optional; JWT tenant is used.
    """
    if not (60 <= payload.access_token_lifespan <= 3600):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="access_token_lifespan must be between 60 and 3600 seconds",
        )
    if not (300 <= payload.sso_session_idle_timeout <= 86400):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sso_session_idle_timeout must be between 300 and 86400 seconds",
        )
    if not (300 <= payload.sso_session_max_lifespan <= 7776000):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sso_session_max_lifespan must be between 300 and 7776000 seconds",
        )

    _require_admin(user)
    resolved_tenant_id = _resolve_db_tenant(user, tenant_id)
    kc = _get_kc_admin(request)
    await kc.update_realm_settings({
        "accessTokenLifespan": payload.access_token_lifespan,
        "ssoSessionIdleTimeout": payload.sso_session_idle_timeout,
        "ssoSessionMaxLifespan": payload.sso_session_max_lifespan,
    })
    logger.info(
        "Session settings updated",
        extra={"tenant_id": resolved_tenant_id, "actor": user.email},
    )
    _maybe_audit(
        request, resolved_tenant_id, user,
        "security.session.update",
        {
            "access_token_lifespan": payload.access_token_lifespan,
            "sso_session_idle_timeout": payload.sso_session_idle_timeout,
            "sso_session_max_lifespan": payload.sso_session_max_lifespan,
        },
    )
    return SessionSettingsResponse(
        access_token_lifespan=payload.access_token_lifespan,
        sso_session_idle_timeout=payload.sso_session_idle_timeout,
        sso_session_max_lifespan=payload.sso_session_max_lifespan,
    )
