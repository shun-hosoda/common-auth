"""Invitation flow router.

Provides two groups of endpoints:

*Admin endpoints* (``/api/admin/invitations/*``)
    Require ``tenant_admin`` or ``super_admin`` JWT.  Used to issue, list,
    revoke, and resend invitations.

*Public endpoints* (``/api/invitations/*``)
    No JWT required — protected by Rate Limiting middleware only.
    Used by the invited user to validate a token and complete registration.

Design references:
    - docs/design/user-management.md §10 (Phase 4 invitation flow)
    - M-1: EmailService via SMTP, not Keycloak
    - M-2: DB pool injected via Depends(get_db_pool)
    - M-3: This file + setup.py include_router
    - M-4: MFA policy check → CONFIGURE_TOTP required action
    - M-5: KC exact email search for duplicate check
    - M-6: Best-effort bulk create — returns succeeded/failed
    - NEW-1: Compensation delete of KC user on DB failure
    - NEW-2: MFA policy fetched from KC group (no JWT in Public API)
    - S-4: resend revokes old token before inserting new one
"""

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Literal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, field_validator

from common_auth.dependencies.current_user import get_current_user
from common_auth.dependencies.db import get_db_conn_bypass_rls, get_db_pool
from common_auth.models.auth_user import AuthUser
from common_auth.services.email_service import EmailService
from common_auth.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_kc_admin(request: Request) -> KeycloakAdminClient:
    """Return cached KeycloakAdminClient (mirrors admin.py pattern)."""
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
    return request.app.state.kc_admin_client


def _get_email_service(request: Request) -> EmailService:
    svc: EmailService | None = getattr(request.app.state, "email_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured",
        )
    return svc


def _require_admin(user: AuthUser) -> None:
    if not ({"tenant_admin", "super_admin"} & set(user.roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_admin or super_admin role required",
        )


async def _get_tenant_row(
    pool: asyncpg.Pool, realm_name: str
) -> asyncpg.Record:
    """Look up tenants row by realm_name; raise 404 if missing."""
    row = await pool.fetchrow(
        "SELECT id, realm_name, display_name FROM tenants WHERE realm_name = $1",
        realm_name,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{realm_name}' not found",
        )
    return row


def _effective_status(status_val: str, expires_at: datetime) -> str:
    """Return 'expired' when a pending invitation is past its deadline."""
    if status_val == "pending" and expires_at < datetime.now(timezone.utc):
        return "expired"
    return status_val


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Convert asyncpg Record and compute effective_status.

    M-3 fix: preserves the original DB ``status`` and adds a separate
    ``effective_status`` key (pending → expired when past deadline).
    """
    d = dict(row)
    d["effective_status"] = _effective_status(d["status"], d["expires_at"])
    return d


# ── Pydantic models ───────────────────────────────────────────────────────────


class InvitationCreateItem(BaseModel):
    email: EmailStr
    role: Literal["user", "tenant_admin"] = "user"
    group_id: UUID | None = None


class InvitationBulkRequest(BaseModel):
    invitations: list[InvitationCreateItem]
    custom_message: str | None = None
    expires_hours: int = 72

    @field_validator("invitations")
    @classmethod
    def check_max_items(cls, v: list) -> list:
        if len(v) > 50:
            raise ValueError("Maximum 50 invitations per request")
        return v

    @field_validator("expires_hours")
    @classmethod
    def check_hours_range(cls, v: int) -> int:
        if not (1 <= v <= 168):
            raise ValueError("expires_hours must be between 1 and 168")
        return v


class InvitationAcceptRequest(BaseModel):
    token: str
    display_name: str
    password: str

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("display_name must not be empty")
        return v.strip()[:200]


# ── Admin endpoints (/api/admin/invitations) ──────────────────────────────────


@router.get("/api/admin/invitations", tags=["invitations"])
async def list_invitations(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    user: AuthUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> list[dict[str, Any]]:
    """List all invitations for the caller's tenant.

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    tenant_row = await _get_tenant_row(pool, user.tenant_id)
    tenant_uuid = tenant_row["id"]

    query = """
        SELECT
            it.id, it.tenant_id, it.email, it.role, it.group_id,
            it.status, it.expires_at, it.accepted_at,
            it.revoked_at, it.revoked_by, it.created_at,
            up.display_name AS invited_by
        FROM invitation_tokens it
        LEFT JOIN user_profiles up ON up.id = it.invited_by
        WHERE it.tenant_id = $1
        ORDER BY it.created_at DESC
    """
    rows = await pool.fetch(query, tenant_uuid)
    result = [_row_to_dict(r) for r in rows]

    if status_filter:
        # S-4 fix: filter on effective_status (accounts for client-side expiry)
        result = [r for r in result if r["effective_status"] == status_filter]

    return result


@router.post("/api/admin/invitations", tags=["invitations"])
async def create_invitations(
    body: InvitationBulkRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict[str, Any]:
    """Issue invitations (up to 50 at once) with best-effort semantics.

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    config = request.app.state.auth_config
    kc = _get_kc_admin(request)
    email_svc = _get_email_service(request)
    tenant_row = await _get_tenant_row(pool, user.tenant_id)
    tenant_uuid = tenant_row["id"]
    tenant_name = tenant_row["display_name"]

    # Look up inviter's display name for the email body.
    # invited_by is NULL when the admin hasn't synced to user_profiles yet
    # (ENABLE_USER_SYNC=false or first login). FK on invited_by is ON DELETE SET NULL.
    inviter_row = await pool.fetchrow(
        "SELECT display_name FROM user_profiles WHERE id = $1",
        UUID(user.sub),
    )
    inviter_name = (inviter_row["display_name"] if inviter_row else None) or user.email
    # Use NULL for invited_by if the admin is not yet in user_profiles (FK guard)
    inviter_uuid: UUID | None = UUID(user.sub) if inviter_row is not None else None

    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_hours)

    succeeded: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []

    for item in body.invitations:
        email = str(item.email).lower()

        # M-5: Check for existing pending invitation (DB)
        existing = await pool.fetchrow(
            "SELECT id FROM invitation_tokens "
            "WHERE tenant_id = $1 AND email = $2 AND status = 'pending'",
            tenant_uuid, email,
        )
        if existing:
            failed.append({"email": email, "reason": "pending_exists"})
            continue

        # M-5: Check if user already exists in this tenant (Keycloak)
        try:
            kc_users = await kc.find_users_by_email(email)
        except Exception as kc_exc:
            logger.error("KC admin lookup failed for %s: %s", email, kc_exc)
            failed.append({"email": email, "reason": "kc_error"})
            continue
        already_member = any(
            user.tenant_id in (u.get("attributes") or {}).get("tenant_id", [])
            for u in kc_users
        )
        if already_member:
            failed.append({"email": email, "reason": "already_member"})
            continue

        # S-1 fix: INSERT + email send wrapped in a single per-item transaction.
        # If SMTP fails the transaction rolls back automatically — no orphaned DB rows.
        token = secrets.token_urlsafe(32)
        inv_row: asyncpg.Record | None = None
        try:
            async with pool.acquire() as item_conn:
                async with item_conn.transaction():
                    inv_row = await item_conn.fetchrow(
                        """
                        INSERT INTO invitation_tokens
                            (tenant_id, email, token, role, group_id, invited_by,
                             custom_message, expires_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id, tenant_id, email, role, group_id, status,
                                  expires_at, accepted_at, revoked_at, created_at
                        """,
                        tenant_uuid, email, token, item.role,
                        item.group_id, inviter_uuid,
                        body.custom_message, expires_at,
                    )
                    # Send email inside transaction — auto-rollback on SMTP failure (S-1)
                    await email_svc.send_invitation(
                        to_email=email,
                        token=token,
                        invited_by_name=inviter_name,
                        tenant_name=tenant_name,
                        base_url=config.invitation_base_url,
                        custom_message=body.custom_message,
                    )
        except asyncpg.UniqueViolationError:
            # Race: another request just created a pending invite for the same email
            failed.append({"email": email, "reason": "pending_exists"})
            continue
        except Exception as exc:
            logger.error("Failed invitation for %s: %s", email, exc, exc_info=True)
            failed.append({"email": email, "reason": "invitation_error"})
            continue

        row_dict = _row_to_dict(inv_row)
        row_dict["invited_by"] = inviter_name
        succeeded.append(row_dict)

    return {"succeeded": succeeded, "failed": failed}


@router.delete(
    "/api/admin/invitations/{invitation_id}",
    tags=["invitations"],
)
async def revoke_invitation(
    invitation_id: UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict[str, Any]:
    """Revoke a pending invitation.

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    tenant_row = await _get_tenant_row(pool, user.tenant_id)
    tenant_uuid = tenant_row["id"]

    row = await pool.fetchrow(
        # S-2 fix: include expires_at so _effective_status can compute correctly
        "SELECT id, status, expires_at FROM invitation_tokens WHERE id = $1 AND tenant_id = $2",
        invitation_id, tenant_uuid,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    eff = _effective_status(row["status"], row["expires_at"])
    if eff in ("accepted", "revoked"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot revoke invitation with status '{eff}'",
        )

    # revoked_by: NULL when admin is not in user_profiles (FK guard)
    revoker_exists = await pool.fetchval(
        "SELECT 1 FROM user_profiles WHERE id = $1", UUID(user.sub)
    )
    revoker_uuid: UUID | None = UUID(user.sub) if revoker_exists else None

    updated = await pool.fetchrow(
        """
        UPDATE invitation_tokens
        SET status = 'revoked', revoked_at = NOW(), revoked_by = $1
        WHERE id = $2
        RETURNING id, tenant_id, email, role, group_id, status,
                  expires_at, accepted_at, revoked_at, created_at
        """,
        revoker_uuid, invitation_id,
    )
    result = _row_to_dict(updated)
    result["invited_by"] = None
    return result


@router.post(
    "/api/admin/invitations/{invitation_id}/resend",
    tags=["invitations"],
)
async def resend_invitation(
    invitation_id: UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict[str, Any]:
    """Revoke the existing invitation and issue a new token. (S-4)

    Requires: tenant_admin or super_admin
    """
    _require_admin(user)
    config = request.app.state.auth_config
    email_svc = _get_email_service(request)
    tenant_row = await _get_tenant_row(pool, user.tenant_id)
    tenant_uuid = tenant_row["id"]
    tenant_name = tenant_row["display_name"]

    old_row = await pool.fetchrow(
        """
        SELECT id, email, role, group_id, status, expires_at, custom_message
        FROM invitation_tokens
        WHERE id = $1 AND tenant_id = $2
        """,
        invitation_id, tenant_uuid,
    )
    if old_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if old_row["status"] == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot resend an already accepted invitation",
        )

    # Look up inviter name
    inviter_row = await pool.fetchrow(
        "SELECT display_name FROM user_profiles WHERE id = $1", UUID(user.sub)
    )
    inviter_name = (inviter_row["display_name"] if inviter_row else None) or user.email
    # Use NULL for revoked_by / invited_by if admin not in user_profiles (FK guard)
    inviter_uuid: UUID | None = UUID(user.sub) if inviter_row is not None else None

    config_obj = request.app.state.auth_config
    expires_hours = getattr(config_obj, "invitation_expires_hours", 72)
    new_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    new_token = secrets.token_urlsafe(32)

    # S-4: revoke old → insert new → send email, all inside single transaction (S-1 pattern).
    # SMTP failure rolls back the DB writes — no orphaned/ghost invitation rows.
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE invitation_tokens SET status='revoked', revoked_at=NOW(), revoked_by=$1 WHERE id=$2",
                inviter_uuid, invitation_id,
            )
            new_row = await conn.fetchrow(
                """
                INSERT INTO invitation_tokens
                    (tenant_id, email, token, role, group_id, invited_by,
                     custom_message, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, tenant_id, email, role, group_id, status,
                          expires_at, accepted_at, revoked_at, created_at
                """,
                tenant_uuid, old_row["email"], new_token, old_row["role"],
                old_row["group_id"], inviter_uuid,
                old_row["custom_message"], new_expires_at,
            )
            # Send email inside transaction — SMTP failure auto-rolls back DB (S-1)
            await email_svc.send_invitation(
                to_email=old_row["email"],
                token=new_token,
                invited_by_name=inviter_name,
                tenant_name=tenant_name,
                base_url=config.invitation_base_url,
                custom_message=old_row["custom_message"],
            )

    result = _row_to_dict(new_row)
    result["invited_by"] = inviter_name
    return result


# ── Public endpoints (/api/invitations) ───────────────────────────────────────


@router.get("/api/invitations/validate", tags=["invitations"])
async def validate_invitation(
    request: Request,
    token: str = Query(..., description="Invitation token from the email URL"),
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict[str, Any]:
    """Validate an invitation token and return invite details.

    Returns 404 for any invalid/expired/used token (timing oracle 防止, S-2 refactored).
    Rate limited: 10 req/min per IP.

    M-4 fix: RLS bypass uses ``SET LOCAL`` inside an explicit transaction.
    M-1 fix: returns all fields expected by ``InvitationValidateResponse``.
    NEW-1 fix: DB connection is acquired and released *before* KC HTTP calls to
               avoid holding a pool connection open during external I/O.
    NEW-2:   fetches MFA policy from KC group without a user JWT.
    """
    # Acquire connection for DB fetch only, then release before KC calls (NEW-1 fix)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL row_security = off")
            row = await conn.fetchrow(
                """
                SELECT it.email, it.role, it.custom_message, it.expires_at,
                       t.display_name AS tenant_display_name,
                       t.realm_name,
                       up.display_name AS inviter_display_name
                FROM invitation_tokens it
                JOIN tenants t ON t.id = it.tenant_id
                LEFT JOIN user_profiles up ON up.id = it.invited_by
                WHERE it.token = $1
                  AND it.status = 'pending'
                  AND it.expires_at > NOW()
                """,
                token,
            )
    # Connection released here — KC calls execute without holding a pool slot

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation")

    # NEW-2: Fetch MFA policy from KC group (no user JWT available in public endpoint)
    kc = _get_kc_admin(request)
    mfa_required = False
    try:
        group = await kc.find_group_by_name(row["realm_name"])
        if group:
            full_group = await kc.get_group(group["id"])
            attrs = full_group.get("attributes") or {}
            mfa_required = attrs.get("mfa_enabled", ["false"])[0] == "true"
    except Exception:
        logger.warning(
            "Could not fetch MFA policy for validate (tenant: %s). Defaulting to false.",
            row["realm_name"], exc_info=True,
        )

    config = request.app.state.auth_config
    pw_hint: str | None = getattr(config, "keycloak_pw_policy_hint", None) or None

    return {
        "valid": True,
        "email": row["email"],
        "role": row["role"],
        "tenant_display_name": row["tenant_display_name"],
        "inviter_display_name": row["inviter_display_name"],
        "custom_message": row["custom_message"],
        "mfa_required": mfa_required,
        "password_policy_hint": pw_hint,
    }


@router.post("/api/invitations/accept", tags=["invitations"])
async def accept_invitation(
    body: InvitationAcceptRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db_conn_bypass_rls),
) -> dict[str, Any]:
    """Accept an invitation: create Keycloak user + DB user_profiles.

    Rate limited: 5 req/min per IP.

    Flow (NEW-1 compensation, NEW-2 MFA policy):
    1. Lock invitation row
    2. Fetch tenant realm_name → look up KC group → get MFA policy (NEW-2)
    3. Create KC user (compensation: delete on failure, NEW-1)
    4. Set KC password / role / attributes / required actions
    5. DB: INSERT user_profiles + optional group membership
    6. DB: UPDATE invitation status = accepted
    """
    kc = _get_kc_admin(request)

    # ── Step 1: Lock the invitation row ──────────────────────────────────────
    inv = await conn.fetchrow(
        """
        SELECT it.id, it.email, it.role, it.group_id, it.tenant_id,
               t.realm_name, t.display_name AS tenant_name
        FROM invitation_tokens it
        JOIN tenants t ON t.id = it.tenant_id
        WHERE it.token = $1
          AND it.status = 'pending'
          AND it.expires_at > NOW()
        FOR UPDATE OF it
        """,
        body.token,
    )
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation",
        )

    email: str = inv["email"]
    role: str = inv["role"]
    realm_name: str = inv["realm_name"]
    tenant_uuid = inv["tenant_id"]

    # ── Step 2: Get MFA policy from KC group (NEW-2) ──────────────────────────
    mfa_enabled = False
    mfa_method = "totp"
    try:
        group = await kc.find_group_by_name(realm_name)
        if group:
            full_group = await kc.get_group(group["id"])
            attrs = full_group.get("attributes") or {}
            mfa_enabled = attrs.get("mfa_enabled", ["false"])[0] == "true"
            mfa_method = attrs.get("mfa_method", ["totp"])[0]
    except Exception:
        logger.warning(
            "Could not fetch MFA policy for tenant '%s'. Defaulting to MFA disabled.",
            realm_name, exc_info=True,
        )

    required_actions: list[str] = []
    if mfa_enabled and mfa_method == "totp":
        required_actions = ["CONFIGURE_TOTP"]

    user_payload: dict[str, Any] = {
        "username": email,
        "email": email,
        "firstName": body.display_name,
        "lastName": "",
        "enabled": True,
        # S-3: emailVerified=True is safe here because the invitation was received
        # at this exact address; the invited user clicked the link from that mailbox.
        # Design decision: trust invite-by-email as implicit address verification.
        "emailVerified": True,
        "attributes": {
            "tenant_id": [realm_name],
            "mfa_enabled": [str(mfa_enabled).lower()],
            "mfa_method": [mfa_method],
        },
        "requiredActions": required_actions,
    }

    # ── Steps 3-6: KC operations with compensation on failure (NEW-1) ──────────
    kc_user_id: str | None = None
    try:
        # 3. Create KC user
        kc_user_id = await kc.create_user(user_payload)

        # 4a. Set password (temporary=False — user chose it themselves)
        try:
            await kc.reset_password(kc_user_id, body.password, temporary=False)
        except Exception as exc:
            # KC PW policy violation returns 400 with a message
            detail = str(exc)
            if "400" in detail:
                config = request.app.state.auth_config
                hint = getattr(config, "keycloak_pw_policy_hint", "")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Password does not meet policy requirements. {hint}".strip(),
                ) from exc
            raise

        # 4b. Assign realm role
        await kc.assign_realm_role(kc_user_id, role)

        # 4c. Add to tenant group
        kc_group = await kc.find_group_by_name(realm_name)
        if kc_group:
            await kc.add_user_to_group(kc_user_id, kc_group["id"])

        # ── Steps 5-6: DB operations (within the bypass-RLS transaction) ─────
        await conn.execute(
            """
            INSERT INTO user_profiles
                (id, tenant_id, email, display_name, email_verified,
                 roles, synced_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, TRUE, $5, NOW(), NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                roles = EXCLUDED.roles,
                synced_at = NOW(),
                updated_at = NOW()
            """,
            UUID(kc_user_id),
            tenant_uuid,
            email,
            body.display_name,
            [role],
        )

        # 5b. Add to DB tenant group if specified
        if inv["group_id"]:
            try:
                await conn.execute(
                    """
                    INSERT INTO user_group_memberships (user_id, group_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    UUID(kc_user_id),
                    inv["group_id"],
                )
            except Exception:
                logger.warning(
                    "Could not add user %s to group %s (best-effort)",
                    kc_user_id, inv["group_id"], exc_info=True,
                )

        # 6. Mark invitation as accepted
        await conn.execute(
            """
            UPDATE invitation_tokens
            SET status = 'accepted', accepted_at = NOW()
            WHERE id = $1
            """,
            inv["id"],
        )

    except HTTPException:
        # Compensation: delete KC user if it was created (NEW-1)
        if kc_user_id:
            try:
                await kc.delete_user(kc_user_id)
                logger.info(
                    "NEW-1 compensation: deleted KC user %s after accept failure", kc_user_id
                )
            except Exception as comp_err:
                logger.error(
                    "NEW-1 COMPENSATION FAILED: KC user %s was NOT deleted. "
                    "Manual cleanup required. Error: %s",
                    kc_user_id, comp_err,
                )
        raise

    except Exception as exc:
        if kc_user_id:
            try:
                await kc.delete_user(kc_user_id)
                logger.info(
                    "NEW-1 compensation: deleted KC user %s after accept failure", kc_user_id
                )
            except Exception as comp_err:
                logger.error(
                    "NEW-1 COMPENSATION FAILED: KC user %s was NOT deleted. "
                    "Manual cleanup required. Error: %s",
                    kc_user_id, comp_err,
                )
        logger.error("accept_invitation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account. Please try again or contact support.",
        ) from exc

    # M-2 fix: return fields matching InvitationAcceptResponse in adminApi.ts
    return {
        "status": "success",
        "mfa_required": mfa_enabled,
        "mfa_method": mfa_method if mfa_enabled else None,
    }
