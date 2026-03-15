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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
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
    return request.app.state.kc_admin_client  # type: ignore[return-value]


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

    new_id = await kc.create_user(payload)

    # Add to tenant group and assign default role in parallel (best-effort)
    if new_id:
        group = await kc.find_group_by_name(user.tenant_id)
        await asyncio.gather(
            kc.add_user_to_group(new_id, group["id"]) if group else asyncio.sleep(0),
            kc.assign_realm_role(new_id, "user"),
            return_exceptions=True,  # best-effort: don't fail on role/group errors
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
