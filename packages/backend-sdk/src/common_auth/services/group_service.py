"""Group service  Etenant_groups CRUD and user_group_memberships management.

All queries are tenant-scoped via DBClient.connection(tenant_id=...) which
applies PostgreSQL RLS automatically.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from common_auth.models.group import GroupCreate, GroupUpdate
from common_auth.services.db_client import DBClient


class GroupService:
    def __init__(self, db: DBClient) -> None:
        self._db = db

    async def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve tenant slug ↁEUUID (pass-through if already a UUID)."""
        return await self._db.resolve_tenant_uuid(tenant_id)

    @staticmethod
    def _to_group_dict(row: Any) -> dict[str, Any]:
        data = dict(row)
        if data.get("tenant_id") is not None:
            data["tenant_id"] = str(data["tenant_id"])
        return data

    # ── Groups CRUD ───────────────────────────────────────────────────────────

    async def list_groups(
        self,
        *,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return paginated list of active groups for the tenant."""
        tenant_id = await self._resolve_tenant(tenant_id)
        offset = (page - 1) * page_size

        async with self._db.connection(tenant_id=tenant_id) as conn:
            if search:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM tenant_groups
                    WHERE tenant_id = $1::uuid AND is_active = true
                      AND name ILIKE $2
                    """,
                    tenant_id,
                    f"%{search}%",
                )
                rows = await conn.fetch(
                    """
                    SELECT g.*,
                           (SELECT COUNT(*) FROM user_group_memberships m
                            WHERE m.group_id = g.id) AS member_count
                    FROM tenant_groups g
                    WHERE g.tenant_id = $1::uuid AND g.is_active = true
                      AND g.name ILIKE $2
                    ORDER BY g.sort_order, g.name
                    LIMIT $3 OFFSET $4
                    """,
                    tenant_id,
                    f"%{search}%",
                    page_size,
                    offset,
                )
            else:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM tenant_groups
                    WHERE tenant_id = $1::uuid AND is_active = true
                    """,
                    tenant_id,
                )
                rows = await conn.fetch(
                    """
                    SELECT g.*,
                           (SELECT COUNT(*) FROM user_group_memberships m
                            WHERE m.group_id = g.id) AS member_count
                    FROM tenant_groups g
                    WHERE g.tenant_id = $1::uuid AND g.is_active = true
                    ORDER BY g.sort_order, g.name
                    LIMIT $2 OFFSET $3
                    """,
                    tenant_id,
                    page_size,
                    offset,
                )

        return {
            "items": [self._to_group_dict(r) for r in rows],
            "total": count,
            "page": page,
            "page_size": page_size,
        }

    async def get_group(
        self, *, tenant_id: str, group_id: uuid.UUID
    ) -> Optional[dict[str, Any]]:
        """Return a single group or None if not found."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT g.*,
                       (SELECT COUNT(*) FROM user_group_memberships m
                        WHERE m.group_id = g.id) AS member_count
                FROM tenant_groups g
                WHERE g.id = $1 AND g.tenant_id = $2::uuid AND g.is_active = true
                """,
                group_id,
                tenant_id,
            )
        return self._to_group_dict(row) if row else None

    async def create_group(
        self, *, tenant_id: str, payload: GroupCreate
    ) -> dict[str, Any]:
        """Insert a new group and return the created record."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_groups
                    (id, tenant_id, name, description, parent_group_id, sort_order)
                VALUES
                    (gen_random_uuid(), $1::uuid, $2, $3, $4, $5)
                RETURNING *,
                    0 AS member_count
                """,
                tenant_id,
                payload.name,
                payload.description,
                payload.parent_group_id,
                payload.sort_order,
            )
        return self._to_group_dict(row)

    async def update_group(
        self,
        *,
        tenant_id: str,
        group_id: uuid.UUID,
        payload: GroupUpdate,
    ) -> Optional[dict[str, Any]]:
        """Update fields on an existing group. Returns None if not found."""
        tenant_id = await self._resolve_tenant(tenant_id)
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return await self.get_group(tenant_id=tenant_id, group_id=group_id)

        set_clauses = ", ".join(
            f"{col} = ${i + 3}"
            for i, col in enumerate(updates.keys())
        )
        values = [group_id, tenant_id, *updates.values()]

        async with self._db.connection(tenant_id=tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE tenant_groups
                SET {set_clauses}, updated_at = NOW()
                WHERE id = $1 AND tenant_id = $2::uuid AND is_active = true
                RETURNING *,
                    (SELECT COUNT(*) FROM user_group_memberships m
                     WHERE m.group_id = tenant_groups.id) AS member_count
                """,
                *values,
            )
        return self._to_group_dict(row) if row else None

    async def delete_group(
        self, *, tenant_id: str, group_id: uuid.UUID
    ) -> bool:
        """Logical delete: set is_active=false, orphan child groups to root."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            # Orphan children
            await conn.execute(
                """
                UPDATE tenant_groups
                SET parent_group_id = NULL, updated_at = NOW()
                WHERE parent_group_id = $1
                  AND tenant_id = $2::uuid
                  AND is_active = true
                """,
                group_id,
                tenant_id,
            )
            deleted_id = await conn.fetchval(
                """
                UPDATE tenant_groups
                SET is_active = false, updated_at = NOW()
                WHERE id = $1 AND tenant_id = $2::uuid AND is_active = true
                RETURNING id
                """,
                group_id,
                tenant_id,
            )
        return deleted_id is not None

    # ── Membership ────────────────────────────────────────────────────────────

    async def list_members(
        self, *, tenant_id: str, group_id: uuid.UUID
    ) -> dict[str, Any]:
        """Return members of a group with their profile info."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_group_memberships WHERE group_id = $1",
                group_id,
            )
            rows = await conn.fetch(
                """
                SELECT m.user_id, p.email, p.display_name, m.joined_at
                FROM user_group_memberships m
                JOIN user_profiles p ON p.id = m.user_id
                WHERE m.group_id = $1
                ORDER BY p.email
                """,
                group_id,
            )
        return {
            "items": [dict(r) for r in rows],
            "total": count,
        }

    async def add_members(
        self,
        *,
        tenant_id: str,
        group_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        added_by: uuid.UUID,
    ) -> None:
        """Bulk-insert user_group_memberships. Ignores duplicate entries."""
        tenant_id = await self._resolve_tenant(tenant_id)
        records = [(group_id, uid, added_by) for uid in user_ids]
        async with self._db.connection(tenant_id=tenant_id) as conn:
            await conn.executemany(
                """
                INSERT INTO user_group_memberships (user_id, group_id, added_by)
                VALUES ($2, $1, $3)
                ON CONFLICT DO NOTHING
                """,
                records,
            )

    async def remove_member(
        self, *, tenant_id: str, group_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Remove a user from a group. Returns True if the row existed."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM user_group_memberships
                WHERE group_id = $1 AND user_id = $2
                """,
                group_id,
                user_id,
            )
        return str(result).endswith("1")

    # ── User ↁEGroup (user-side operations) ──────────────────────────────────

    async def list_user_groups(
        self, *, tenant_id: str, user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Return all groups a user belongs to."""
        tenant_id = await self._resolve_tenant(tenant_id)
        async with self._db.connection(tenant_id=tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT g.id AS group_id, g.name AS group_name,
                       g.parent_group_id, m.joined_at
                FROM user_group_memberships m
                JOIN tenant_groups g ON g.id = m.group_id
                WHERE m.user_id = $1
                  AND g.tenant_id = $2::uuid
                  AND g.is_active = true
                ORDER BY g.name
                """,
                user_id,
                tenant_id,
            )
        return [dict(r) for r in rows]

    async def add_user_to_group(
        self,
        *,
        tenant_id: str,
        user_id: uuid.UUID,
        group_id: uuid.UUID,
        added_by: uuid.UUID,
    ) -> None:
        """Add a single user to a group (idempotent)."""
        await self.add_members(
            tenant_id=tenant_id,
            group_id=group_id,
            user_ids=[user_id],
            added_by=added_by,
        )

    async def remove_user_from_group(
        self,
        *,
        tenant_id: str,
        user_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> bool:
        return await self.remove_member(
            tenant_id=tenant_id, group_id=group_id, user_id=user_id
        )
