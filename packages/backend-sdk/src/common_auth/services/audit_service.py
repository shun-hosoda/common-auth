"""Audit log service — best-effort background write to audit_logs table.

All management operations (group mutations, security setting changes etc.)
call ``AuditService.log()`` after the main operation succeeds.  The write
is dispatched as a fire-and-forget ``asyncio.create_task()`` so that a DB
failure never blocks or rolls back the caller's transaction.

Failure visibility:
  - Every failure is logged as ``logger.error("audit_log_write_failed", ...)``
    with structured extra fields (action, tenant_id, actor_id, error).
  - ``_failure_count`` is incremented per failure and can be exposed to
    monitoring systems (Prometheus etc.) in future.

Usage::

    async with request.app.state.db.connection(tenant_id=tenant_id) as conn:
        # ... main operation ...
        pass

    audit_svc = AuditService(request.app.state.db)
    asyncio.create_task(
        audit_svc.log(
            tenant_id=tenant_id,
            actor_id=user.sub,
            actor_email=user.email,
            action="group.member.add",
            resource_type="group",
            resource_id=str(group_id),
            details={"user_id": str(user_id)},
        )
    )
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from common_auth.services.db_client import DBClient

logger = logging.getLogger(__name__)

_INSERT_SQL = """
INSERT INTO audit_logs
    (tenant_id, actor_id, actor_email, action,
     resource_type, resource_id, details, ip_address, user_agent)
VALUES
    ($1, $2, $3, $4, $5, $6, $7, $8::inet, $9)
"""


@dataclass
class AuditEntry:
    """Immutable value object representing a single audit event."""

    tenant_id: str
    actor_id: str | None
    actor_email: str | None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None


class AuditService:
    """Write audit log entries to the ``audit_logs`` PostgreSQL table.

    This service is designed to be instantiated per-request (lightweight;
    it holds only a reference to the shared DBClient pool).
    """

    def __init__(self, db: DBClient) -> None:
        self._db = db
        self._failure_count: int = 0  # visible to monitoring (e.g. Prometheus)

    # ── Public API ────────────────────────────────────────────────────────────

    def log(
        self,
        *,
        tenant_id: str,
        actor_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "asyncio.Task[None]":
        """Fire-and-forget audit write.  Returns the Task if callers need it.

        Typical usage::

            asyncio.create_task(
                audit_svc.log(tenant_id=..., action="group.member.add", ...)
            )

        Failures are silenced from the caller's perspective but are always
        recorded via structured logging and the internal failure counter.
        """
        entry = AuditEntry(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return asyncio.ensure_future(self._write(entry))

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _write(self, entry: AuditEntry) -> None:
        """Persist *entry* to the DB.  Never raises; failures are logged."""
        try:
            actor_uuid: uuid.UUID | None = None
            if entry.actor_id:
                try:
                    actor_uuid = uuid.UUID(entry.actor_id)
                except ValueError:
                    pass  # keep None if actor_id is not a valid UUID

            resolved_tenant = await self._db.resolve_tenant_uuid(entry.tenant_id)
            tenant_uuid = uuid.UUID(resolved_tenant)

            async with self._db.connection(tenant_id=resolved_tenant) as conn:
                await conn.execute(
                    _INSERT_SQL,
                    tenant_uuid,
                    actor_uuid,
                    entry.actor_email,
                    entry.action,
                    entry.resource_type,
                    entry.resource_id,
                    entry.details,
                    entry.ip_address,
                    entry.user_agent,
                )
        except Exception as exc:  # noqa: BLE001
            self._failure_count += 1
            logger.error(
                "audit_log_write_failed",
                extra={
                    "action": entry.action,
                    "tenant_id": entry.tenant_id,
                    "actor_id": entry.actor_id,
                    "error": str(exc),
                },
            )

    # ── Query ─────────────────────────────────────────────────────────────────

    async def list_logs(
        self,
        *,
        tenant_id: str,
        action_prefix: str | None = None,
        actor_id: str | None = None,
        from_dt: str | None = None,
        to_dt: str | None = None,
        page: int = 1,
        per_page: int = 50,
        is_super_admin: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated audit logs and total count.

        Args:
            tenant_id:     Target tenant ID (resolved by caller).
            action_prefix: Filter by action prefix, e.g. ``group.*``
                           (trailing ``*`` is replaced with SQL ``LIKE`` pattern).
            actor_id:      Filter by actor UUID string.
            from_dt:       ISO-8601 lower bound for ``created_at`` (inclusive).
            to_dt:         ISO-8601 upper bound for ``created_at`` (inclusive).
            page:          1-based page number.
            per_page:      Records per page (max 200).
            is_super_admin: When True use ``skip_rls=True`` (cross-tenant read).
        """
        per_page = min(per_page, 200)
        offset = (page - 1) * per_page

        tenant_id = await self._db.resolve_tenant_uuid(tenant_id)

        conditions: list[str] = ["tenant_id = $1"]
        params: list[Any] = [uuid.UUID(tenant_id)]
        idx = 2  # next param index

        if action_prefix:
            pattern = action_prefix.rstrip("*") + "%"
            conditions.append(f"action LIKE ${idx}")
            params.append(pattern)
            idx += 1

        if actor_id:
            conditions.append(f"actor_id = ${idx}")
            params.append(uuid.UUID(actor_id))
            idx += 1

        if from_dt:
            conditions.append(f"created_at >= ${idx}")
            params.append(from_dt)
            idx += 1

        if to_dt:
            conditions.append(f"created_at <= ${idx}")
            params.append(to_dt)
            idx += 1

        where = " AND ".join(conditions)
        count_sql = f"SELECT COUNT(*) FROM audit_logs WHERE {where}"
        rows_sql = (
            f"SELECT id, tenant_id, actor_id, actor_email, action, "
            f"resource_type, resource_id, details, ip_address, user_agent, created_at "
            f"FROM audit_logs WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        )
        params_full = params + [per_page, offset]

        async with self._db.connection(
            tenant_id=tenant_id, skip_rls=is_super_admin
        ) as conn:
            total: int = await conn.fetchval(count_sql, *params)
            rows = await conn.fetch(rows_sql, *params_full)

        logs = [
            {
                "id": str(r["id"]),
                "tenant_id": str(r["tenant_id"]),
                "actor_id": str(r["actor_id"]) if r["actor_id"] else None,
                "actor_email": r["actor_email"],
                "action": r["action"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "details": dict(r["details"]) if r["details"] else {},
                "ip_address": str(r["ip_address"]) if r["ip_address"] else None,
                "user_agent": r["user_agent"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
        return logs, total
