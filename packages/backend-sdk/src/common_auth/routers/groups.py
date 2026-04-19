"""Groups router — /admin/groups endpoints.

Provides:
  GET    /admin/groups
  POST   /admin/groups
  GET    /admin/groups/{group_id}
  PUT    /admin/groups/{group_id}
  DELETE /admin/groups/{group_id}
  GET    /admin/groups/{group_id}/members
  POST   /admin/groups/{group_id}/members
  DELETE /admin/groups/{group_id}/members/{user_id}
  GET    /admin/groups/{group_id}/permissions
  PUT    /admin/groups/{group_id}/permissions
  GET    /admin/permissions               (master list)

User-side group/permission endpoints are in admin.py:
  GET    /admin/users/{user_id}/groups
  POST   /admin/users/{user_id}/groups
  DELETE /admin/users/{user_id}/groups/{group_id}
  GET    /admin/users/{user_id}/permissions
  PUT    /admin/users/{user_id}/permissions
"""

import uuid
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from common_auth.dependencies.current_user import get_current_user
from common_auth.models.auth_user import AuthUser
from common_auth.models.group import (
    AddMembersRequest,
    BulkPermissionUpdateRequest,
    GroupCreate,
    GroupListResponse,
    GroupResponse,
    GroupUpdate,
    PermissionEntry,
    MembersListResponse,
    PermissionsListResponse,
)
from common_auth.services.db_client import DBClient
from common_auth.services.group_service import GroupService
from common_auth.services.permission_service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_admin(user: AuthUser) -> None:
    if not ({"tenant_admin", "super_admin"} & set(user.roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_admin or super_admin role required",
        )


def _get_services(request: Request) -> tuple[GroupService, PermissionService]:
    db: DBClient = request.app.state.db
    return GroupService(db), PermissionService(db)


def _resolve_tenant(user: AuthUser, target_tenant: Optional[str] = None) -> str:
    """Return the effective tenant_id for the operation."""
    if "super_admin" in user.roles and target_tenant:
        return target_tenant
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id not found in token",
        )
    return user.tenant_id


# ── Group CRUD ────────────────────────────────────────────────────────────────


@router.get("/groups", response_model=GroupListResponse)
async def list_groups(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
) -> GroupListResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    result = await group_svc.list_groups(
        tenant_id=tenant_id, page=page, page_size=page_size, search=search
    )
    return GroupListResponse(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: Request,
    payload: GroupCreate,
    user: AuthUser = Depends(get_current_user),
) -> GroupResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    row = await group_svc.create_group(tenant_id=tenant_id, payload=payload)
    return GroupResponse(**row)


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    request: Request,
    group_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> GroupResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    row = await group_svc.get_group(tenant_id=tenant_id, group_id=group_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return GroupResponse(**row)


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    request: Request,
    group_id: uuid.UUID,
    payload: GroupUpdate,
    user: AuthUser = Depends(get_current_user),
) -> GroupResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    row = await group_svc.update_group(
        tenant_id=tenant_id, group_id=group_id, payload=payload
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return GroupResponse(**row)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    request: Request,
    group_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> None:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    deleted = await group_svc.delete_group(tenant_id=tenant_id, group_id=group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


# ── Members ───────────────────────────────────────────────────────────────────


@router.get("/groups/{group_id}/members", response_model=MembersListResponse)
async def list_members(
    request: Request,
    group_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> MembersListResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    result = await group_svc.list_members(tenant_id=tenant_id, group_id=group_id)
    return MembersListResponse(**result)


@router.post("/groups/{group_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_members(
    request: Request,
    group_id: uuid.UUID,
    payload: AddMembersRequest,
    user: AuthUser = Depends(get_current_user),
) -> None:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    await group_svc.add_members(
        tenant_id=tenant_id,
        group_id=group_id,
        user_ids=payload.user_ids,
        added_by=uuid.UUID(user.sub),
    )


@router.delete(
    "/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    request: Request,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> None:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    group_svc, _ = _get_services(request)

    removed = await group_svc.remove_member(
        tenant_id=tenant_id, group_id=group_id, user_id=user_id
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )


# ── Group Permissions ─────────────────────────────────────────────────────────


@router.get("/groups/{group_id}/permissions", response_model=PermissionsListResponse)
async def list_group_permissions(
    request: Request,
    group_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
) -> PermissionsListResponse:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    _, perm_svc = _get_services(request)

    items = await perm_svc.list_group_permissions(
        tenant_id=tenant_id, group_id=group_id
    )
    return PermissionsListResponse(
        permissions=[PermissionEntry(**item) for item in items]
    )


@router.put("/groups/{group_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def update_group_permissions(
    request: Request,
    group_id: uuid.UUID,
    payload: BulkPermissionUpdateRequest,
    user: AuthUser = Depends(get_current_user),
) -> None:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    _, perm_svc = _get_services(request)

    await perm_svc.update_group_permissions(
        tenant_id=tenant_id,
        group_id=group_id,
        updates=payload.permissions,
        granted_by=uuid.UUID(user.sub),
    )


# ── Permission master list ────────────────────────────────────────────────────


@router.get("/permissions")
async def list_permissions(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    _require_admin(user)
    tenant_id = _resolve_tenant(user)
    _, perm_svc = _get_services(request)

    items = await perm_svc.list_permissions(tenant_id=tenant_id)
    return {"permissions": items}
