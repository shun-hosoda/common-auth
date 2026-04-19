"""Pydantic models for Group management API.

Covers:
- tenant_groups CRUD
- user_group_memberships
- permissions (group / user)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Group ──────────────────────────────────────────────────────────────────────


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    parent_group_id: Optional[uuid.UUID] = None
    sort_order: int = 0


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    parent_group_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = None


class GroupResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    name: str
    description: Optional[str]
    parent_group_id: Optional[uuid.UUID]
    is_active: bool
    sort_order: int
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class GroupListResponse(BaseModel):
    items: list[GroupResponse]
    total: int
    page: int
    page_size: int


# ── Membership ─────────────────────────────────────────────────────────────────


class AddMembersRequest(BaseModel):
    """Bulk add members to a group."""
    user_ids: list[uuid.UUID] = Field(..., min_length=1)


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: Optional[str]
    joined_at: datetime


class MembersListResponse(BaseModel):
    items: list[MemberResponse]
    total: int


# ── Permission ─────────────────────────────────────────────────────────────────


class PermissionDefinition(BaseModel):
    """A permission definition from the permissions table."""
    id: uuid.UUID
    resource: str
    action: str
    description: Optional[str]
    is_system: bool


class PermissionEntry(BaseModel):
    """A permission definition with its current granted status.

    granted=True  : 許可
    granted=False : 明示的拒否
    granted=None  : 未設定（デフォルト拒否）
    """
    id: uuid.UUID
    resource: str
    action: str
    description: Optional[str]
    is_system: bool
    granted: Optional[bool]  # None = no record (default deny)


class PermissionUpdate(BaseModel):
    """Single entry in bulk permission update payload."""
    permission_id: uuid.UUID
    granted: Optional[bool]  # None = DELETE the record (reset to default deny)


class BulkPermissionUpdateRequest(BaseModel):
    permissions: list[PermissionUpdate]


class PermissionsListResponse(BaseModel):
    permissions: list[PermissionEntry]


# ── User groups / effective permissions ────────────────────────────────────────


class UserGroupEntry(BaseModel):
    group_id: uuid.UUID
    group_name: str
    parent_group_id: Optional[uuid.UUID]
    joined_at: datetime


class UserGroupsResponse(BaseModel):
    groups: list[UserGroupEntry]


class EffectivePermissionEntry(BaseModel):
    """Effective permission after resolving group + user-direct rules."""
    id: uuid.UUID
    resource: str
    action: str
    granted: bool
    source: str  # "user_direct" | "group:<group_name>" | "default_deny"


class EffectivePermissionsResponse(BaseModel):
    permissions: list[EffectivePermissionEntry]
