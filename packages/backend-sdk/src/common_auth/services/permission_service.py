"""Permission service  Egroup/user permission management and effective resolution.

Implements the 2-layer permission model:
  Priority (high ↁElow):
  1. user_permissions (granted=False)  Eexplicit deny
  2. user_permissions (granted=True)   Eexplicit allow
  3. group_permissions (any group, granted=False)  Egroup deny
  4. group_permissions (any group, granted=True)   Egroup allow
  5. default ↁEdeny
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from common_auth.models.group import PermissionUpdate
from common_auth.services.db_client import DBClient


class PermissionService:
    def __init__(self, db: DBClient) -> None:
        self._db = db

    async def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve tenant slug ↁEUUID."""
        return await self._db.resolve_tenant_uuid(tenant_id)

    # ── Permission master ─────────────────────────────────────────────────────

    async def list_permissions(
        self, *, tenant_id: str
    ) -> list[dict[str, Any]]:
        """Return all permission definitions visible to this tenant.

        Includes system permissions (tenant_id IS NULL) and tenant-custom ones.
        """
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT id, resource, action, description, is_system, tenant_id
                FROM permissions
                WHERE tenant_id IS NULL OR tenant_id = $1::uuid
                ORDER BY resource, action
                """,
                tenant_id,
            )
        return [dict(r) for r in rows]

    # ── Group permissions ─────────────────────────────────────────────────────

    async def list_group_permissions(
        self, *, tenant_id: str, group_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Return all permission definitions with their current granted status for a group.

        granted = True  ↁEgroup_permissions record has granted=true
        granted = False ↁEgroup_permissions record has granted=false (explicit deny)
        granted = None  ↁEno record (default deny)
        """
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT p.id, p.resource, p.action, p.description, p.is_system,
                       gp.granted
                FROM permissions p
                LEFT JOIN group_permissions gp
                       ON gp.permission_id = p.id AND gp.group_id = $1
                WHERE p.tenant_id IS NULL OR p.tenant_id = $2::uuid
                ORDER BY p.resource, p.action
                """,
                group_id,
                tenant_id,
            )
        return [dict(r) for r in rows]

    async def update_group_permissions(
        self,
        *,
        tenant_id: str,
        group_id: uuid.UUID,
        updates: list[PermissionUpdate],
        granted_by: uuid.UUID,
    ) -> None:
        """Bulk-update group permissions.

        - granted=True/False  ↁEUPSERT into group_permissions
        - granted=None        ↁEDELETE from group_permissions (reset to default deny)
        """
        tenant_id = await self._resolve_tenant(tenant_id)
        upserts = [u for u in updates if u.granted is not None]
        deletes = [u for u in updates if u.granted is None]

        async with self._db.connection(tenant_id=tenant_id) as conn:
            if upserts:
                for u in upserts:
                    await conn.execute(
                        """
                        INSERT INTO group_permissions
                            (group_id, permission_id, granted, granted_by, granted_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (group_id, permission_id)
                        DO UPDATE SET granted = EXCLUDED.granted,
                                      granted_by = EXCLUDED.granted_by,
                                      granted_at = NOW()
                        """,
                        group_id,
                        u.permission_id,
                        u.granted,
                        granted_by,
                    )

            if deletes:
                delete_ids = [u.permission_id for u in deletes]
                await conn.execute(
                    """
                    DELETE FROM group_permissions
                    WHERE group_id = $1 AND permission_id = ANY($2::uuid[])
                    """,
                    group_id,
                    delete_ids,
                )

    # ── User permissions ──────────────────────────────────────────────────────

    async def update_user_permissions(
        self,
        *,
        tenant_id: str,
        user_id: uuid.UUID,
        updates: list[PermissionUpdate],
        granted_by: uuid.UUID,
    ) -> None:
        """Bulk-update user direct permissions.

        - granted=True/False  ↁEUPSERT into user_permissions
        - granted=None        ↁEDELETE (revert to group-inherited)
        """
        tenant_id = await self._resolve_tenant(tenant_id)
        upserts = [u for u in updates if u.granted is not None]
        deletes = [u for u in updates if u.granted is None]

        async with self._db.connection(tenant_id=tenant_id) as conn:
            if upserts:
                for u in upserts:
                    await conn.execute(
                        """
                        INSERT INTO user_permissions
                            (user_id, permission_id, granted, granted_by, granted_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (user_id, permission_id)
                        DO UPDATE SET granted = EXCLUDED.granted,
                                      granted_by = EXCLUDED.granted_by,
                                      granted_at = NOW()
                        """,
                        user_id,
                        u.permission_id,
                        u.granted,
                        granted_by,
                    )

            if deletes:
                delete_ids = [u.permission_id for u in deletes]
                await conn.execute(
                    """
                    DELETE FROM user_permissions
                    WHERE user_id = $1 AND permission_id = ANY($2::uuid[])
                    """,
                    user_id,
                    delete_ids,
                )

    # ── Effective permission resolution ───────────────────────────────────────

    async def get_effective_permissions(
        self, *, tenant_id: str, user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Resolve the effective permissions for a user.

        Uses the CTE from docs/design/user-group-permission.md.
        Returns list of {id, resource, action, granted, source}.
        """
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            rows = await conn.fetch(
                """
                WITH all_perms AS (
                    SELECT p.id, p.resource, p.action, p.description
                    FROM permissions p
                    WHERE p.tenant_id IS NULL OR p.tenant_id = $1::uuid
                ),
                user_direct AS (
                    SELECT up.permission_id, up.granted, 'user_direct' AS source
                    FROM user_permissions up
                    WHERE up.user_id = $2
                ),
                group_perms AS (
                    SELECT gp.permission_id,
                           gp.granted,
                           g.name AS group_name
                    FROM user_group_memberships ugm
                    JOIN tenant_groups g ON g.id = ugm.group_id AND g.is_active = true
                    JOIN group_permissions gp ON gp.group_id = ugm.group_id
                    WHERE ugm.user_id = $2
                      AND g.tenant_id = $1::uuid
                ),
                resolved AS (
                    SELECT
                        ap.id,
                        ap.resource,
                        ap.action,
                        CASE
                            WHEN ud.permission_id IS NOT NULL THEN ud.granted
                            WHEN bool_or(gp.granted = false) OVER (PARTITION BY ap.id) THEN false
                            WHEN bool_or(gp.granted = true)  OVER (PARTITION BY ap.id) THEN true
                            ELSE false
                        END AS granted,
                        CASE
                            WHEN ud.permission_id IS NOT NULL THEN ud.source
                            WHEN gp.permission_id IS NOT NULL THEN 'group:' || gp.group_name
                            ELSE 'default_deny'
                        END AS source
                    FROM all_perms ap
                    LEFT JOIN user_direct ud ON ud.permission_id = ap.id
                    LEFT JOIN group_perms gp ON gp.permission_id = ap.id
                )
                SELECT DISTINCT ON (id) id, resource, action, granted, source
                FROM resolved
                ORDER BY id, CASE WHEN source = 'user_direct' THEN 0 ELSE 1 END
                """,
                tenant_id,
                user_id,
            )
        return [dict(r) for r in rows]

    async def list_user_permissions(
        self, *, tenant_id: str, user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """List permissions with current granted status for a user (direct only)."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT p.id, p.resource, p.action, p.description, p.is_system,
                       up.granted
                FROM permissions p
                LEFT JOIN user_permissions up
                       ON up.permission_id = p.id AND up.user_id = $1
                WHERE p.tenant_id IS NULL OR p.tenant_id = $2::uuid
                ORDER BY p.resource, p.action
                """,
                user_id,
                tenant_id,
            )
        return [dict(r) for r in rows]
