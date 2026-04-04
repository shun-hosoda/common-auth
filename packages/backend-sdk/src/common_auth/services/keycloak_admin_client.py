"""Keycloak Admin REST API client using OAuth 2.0 client_credentials grant."""

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class _TokenCache:
    """Thread-safe in-memory access token cache."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    def is_valid(self) -> bool:
        # Keep 30-second safety buffer before actual expiry
        return self._token is not None and time.monotonic() < self._expires_at - 30

    def set(self, token: str, expires_in: int) -> None:
        self._token = token
        self._expires_at = time.monotonic() + expires_in

    def get(self) -> str | None:
        return self._token if self.is_valid() else None


class KeycloakAdminClient:
    """
    Keycloak Admin REST API client.

    Authenticates via OAuth 2.0 client_credentials grant so that
    no end-user token is ever forwarded to the Admin API.
    The caller's JWT is validated separately by the FastAPI middleware;
    this client only talks Keycloak-to-Keycloak with a service account.

    Usage::

        client = KeycloakAdminClient(
            keycloak_url="http://localhost:8080",
            realm="common-auth",
            client_id="admin-api-client",
            client_secret=os.environ["KC_ADMIN_CLIENT_SECRET"],
        )
        users = await client.list_users(tenant_id="acme-corp")
    """

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self._admin_base = f"{self.keycloak_url}/admin/realms/{realm}"
        self._token_url = (
            f"{self.keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        )
        self._cache = _TokenCache()
        self._refresh_lock = asyncio.Lock()
        # Persistent client enables connection pooling across requests.
        # KeycloakAdminClient is a singleton stored in app.state so this
        # client lives for the lifetime of the application.
        self._http = httpx.AsyncClient(timeout=10.0)

    # ── Token management ─────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        """Return a valid admin access token, refreshing when needed."""
        cached = self._cache.get()
        if cached:
            return cached

        async with self._refresh_lock:
            # Double-check after lock acquisition
            cached = self._cache.get()
            if cached:
                return cached

            resp = await self._http.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()

            token: str = data["access_token"]
            expires_in: int = data.get("expires_in", 300)
            self._cache.set(token, expires_in)
            logger.debug(
                "Acquired Keycloak admin token (expires_in=%d)", expires_in
            )
            return token

    # ── Low-level HTTP ────────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Authenticated request to Keycloak Admin REST API."""
        token = await self._get_token()
        resp = await self._http.request(
            method,
            f"{self._admin_base}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            **kwargs,
        )
        return resp

    # ── User operations ───────────────────────────────────────────────────────

    async def list_users(
        self,
        *,
        tenant_id: str | None = None,
        max_results: int = 200,
    ) -> list[dict[str, Any]]:
        """
        List users.  When *tenant_id* is provided, results are filtered to
        users whose ``tenant_id`` attribute matches exactly.
        """
        params: dict[str, Any] = {"max": max_results}
        if tenant_id:
            params["q"] = f"tenant_id:{tenant_id}"

        resp = await self._request("GET", "/users", params=params)
        resp.raise_for_status()
        users: list[dict[str, Any]] = resp.json()

        # Server-side ``q`` filter may return partial matches; apply
        # an exact client-side filter as a safety net.
        if tenant_id:
            users = [
                u
                for u in users
                if tenant_id
                in (u.get("attributes") or {}).get("tenant_id", [])
            ]
        return users

    async def get_user(self, user_id: str) -> dict[str, Any]:
        resp = await self._request("GET", f"/users/{user_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_user(self, payload: dict[str, Any]) -> str:
        """Create a user and return the new user UUID."""
        resp = await self._request("POST", "/users", json=payload)
        resp.raise_for_status()
        location = resp.headers.get("Location", "")
        return location.split("/")[-1]

    async def update_user(self, user_id: str, payload: dict[str, Any]) -> None:
        resp = await self._request("PUT", f"/users/{user_id}", json=payload)
        resp.raise_for_status()

    async def disable_user(self, user_id: str) -> None:
        """Logical delete: disable the user without removing Keycloak data."""
        resp = await self._request(
            "PUT", f"/users/{user_id}", json={"enabled": False}
        )
        resp.raise_for_status()

    async def delete_user(self, user_id: str) -> None:
        """Permanently delete a Keycloak user.

        Used as a compensation action when the invitation accept flow fails
        after Keycloak user creation but before DB commit (NEW-1).
        A 404 is treated as success (user already absent).
        """
        resp = await self._request("DELETE", f"/users/{user_id}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    async def find_users_by_email(self, email: str) -> list[dict[str, Any]]:
        """Return users with an exact email match.

        Uses Keycloak’s ``?email=&exact=true`` query to avoid false positives.
        """
        resp = await self._request(
            "GET", "/users", params={"email": email, "exact": "true"}
        )
        resp.raise_for_status()
        return resp.json()

    async def reset_password(
        self,
        user_id: str,
        new_password: str,
        temporary: bool = True,
    ) -> None:
        resp = await self._request(
            "PUT",
            f"/users/{user_id}/reset-password",
            json={"type": "password", "value": new_password, "temporary": temporary},
        )
        resp.raise_for_status()

    async def reset_mfa(self, user_id: str) -> None:
        """Remove all OTP credentials from the user (MFA reset)."""
        resp = await self._request("GET", f"/users/{user_id}/credentials")
        resp.raise_for_status()
        for cred in resp.json():
            if cred.get("type") == "otp":
                del_resp = await self._request(
                    "DELETE", f"/users/{user_id}/credentials/{cred['id']}"
                )
                del_resp.raise_for_status()

    async def logout_user(self, user_id: str) -> None:
        """
        Delete all active Keycloak SSO sessions for the user.

        After calling this, the user must re-authenticate on their next request.
        This is called after MFA is enabled/changed so users are forced to go
        through the full authentication flow (including the MFA gate) on next login.
        """
        resp = await self._request("POST", f"/users/{user_id}/logout")
        # 204 = success, 404 = user has no active sessions (OK to ignore)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    async def get_user_credentials(self, user_id: str) -> list[dict[str, Any]]:
        """Return the credential list for a user."""
        resp = await self._request("GET", f"/users/{user_id}/credentials")
        resp.raise_for_status()
        return resp.json()

    async def find_group_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a realm group (or subgroup) by exact name."""
        resp = await self._request(
            "GET", "/groups", params={"search": name, "exact": "true"}
        )
        resp.raise_for_status()

        def _find(lst: list[dict[str, Any]]) -> dict[str, Any] | None:
            for g in lst:
                if g["name"] == name:
                    return g
                found = _find(g.get("subGroups", []))
                if found:
                    return found
            return None

        return _find(resp.json())

    async def add_user_to_group(self, user_id: str, group_id: str) -> None:
        resp = await self._request("PUT", f"/users/{user_id}/groups/{group_id}")
        resp.raise_for_status()

    async def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm-level role to a user by name."""
        resp = await self._request("GET", "/roles")
        resp.raise_for_status()
        role = next((r for r in resp.json() if r["name"] == role_name), None)
        if not role:
            logger.warning("Role '%s' not found in realm", role_name)
            return
        resp2 = await self._request(
            "POST",
            f"/users/{user_id}/role-mappings/realm",
            json=[role],
        )
        resp2.raise_for_status()

    # ── Group operations ─────────────────────────────────────────────────────

    async def get_group(self, group_id: str) -> dict[str, Any]:
        """Fetch a single group by UUID, including its attributes."""
        resp = await self._request("GET", f"/groups/{group_id}")
        resp.raise_for_status()
        return resp.json()

    async def update_group_attributes(
        self,
        group_id: str,
        attrs: dict[str, list[str]],
    ) -> None:
        """Merge *attrs* into the group's existing attributes and save.

        Existing attributes not in *attrs* are preserved.
        """
        group = await self.get_group(group_id)
        existing = group.get("attributes") or {}
        existing.update(attrs)
        group["attributes"] = existing
        resp = await self._request("PUT", f"/groups/{group_id}", json=group)
        resp.raise_for_status()

    # ── Bulk user operations (MFA policy) ─────────────────────────────────────

    async def set_user_attributes_bulk(
        self,
        user_ids: list[str],
        attrs: dict[str, list[str]],
    ) -> list[str]:
        """Merge *attrs* into each user's attributes.

        Returns a list of user IDs that **failed** to update.
        """
        failed: list[str] = []
        for uid in user_ids:
            try:
                user = await self.get_user(uid)
                existing = user.get("attributes") or {}
                existing.update(attrs)
                user["attributes"] = existing
                await self.update_user(uid, user)
            except Exception:
                logger.warning("Failed to set attributes for user %s", uid, exc_info=True)
                failed.append(uid)
        return failed

    async def add_required_action_bulk(
        self,
        user_ids: list[str],
        action: str,
    ) -> list[str]:
        """Add *action* to each user's requiredActions (skip if already present).

        Returns a list of user IDs that **failed** to update.

        NOTE: Keycloak's PUT /users/{id} is a **full replace**.  Sending a
        partial payload (e.g. only ``requiredActions``) resets all other
        fields – including ``attributes`` – to empty.  We therefore always
        PUT the complete user representation.
        """
        failed: list[str] = []
        for uid in user_ids:
            try:
                user = await self.get_user(uid)
                actions: list[str] = user.get("requiredActions") or []
                if action not in actions:
                    actions.append(action)
                    user["requiredActions"] = actions
                    await self.update_user(uid, user)
            except Exception:
                logger.warning("Failed to add required action for user %s", uid, exc_info=True)
                failed.append(uid)
        return failed

    async def remove_required_action_bulk(
        self,
        user_ids: list[str],
        action: str,
    ) -> list[str]:
        """Remove *action* from each user's requiredActions (skip if absent).

        Returns a list of user IDs that **failed** to update.

        NOTE: Same full-replace caveat as ``add_required_action_bulk``.
        """
        failed: list[str] = []
        for uid in user_ids:
            try:
                user = await self.get_user(uid)
                actions: list[str] = user.get("requiredActions") or []
                if action in actions:
                    actions.remove(action)
                    user["requiredActions"] = actions
                    await self.update_user(uid, user)
            except Exception:
                logger.warning("Failed to remove required action for user %s", uid, exc_info=True)
                failed.append(uid)
        return failed

    # ── Client (tenant) operations ────────────────────────────────────────────

    _INTERNAL_CLIENT_PREFIXES = (
        "security-admin-console",
        "master-realm",
        "broker",
        "account",
        "account-console",
        "admin-cli",
        "realm-management",
    )

    async def list_clients(self) -> list[dict[str, Any]]:
        """List all non-internal clients in the realm."""
        resp = await self._request("GET", "/clients", params={"max": 100})
        resp.raise_for_status()
        return [
            c
            for c in resp.json()
            if not any(
                c.get("clientId", "").startswith(p)
                for p in self._INTERNAL_CLIENT_PREFIXES
            )
        ]

    async def create_client(self, payload: dict[str, Any]) -> str:
        """Create a new Keycloak client and return its UUID."""
        resp = await self._request("POST", "/clients", json=payload)
        resp.raise_for_status()
        location = resp.headers.get("Location", "")
        return location.split("/")[-1]
