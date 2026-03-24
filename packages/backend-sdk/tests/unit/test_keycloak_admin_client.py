"""Unit tests for KeycloakAdminClient MFA-related methods (Step 1).

Tests 1-1 through 1-5: get_group, update_group_attributes,
set_user_attributes_bulk, add_required_action_bulk, remove_required_action_bulk.

Uses pytest-httpx to mock HTTP requests at the httpx.AsyncClient level.
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from common_auth.services.keycloak_admin_client import KeycloakAdminClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

KC_URL = "http://localhost:8080"
REALM = "common-auth"
ADMIN_BASE = f"{KC_URL}/admin/realms/{REALM}"
TOKEN_URL = f"{KC_URL}/realms/{REALM}/protocol/openid-connect/token"

TOKEN_RESPONSE = {
    "access_token": "mock-admin-token",
    "expires_in": 300,
    "token_type": "Bearer",
}


@pytest.fixture()
def kc(httpx_mock: HTTPXMock) -> KeycloakAdminClient:
    """KeycloakAdminClient with token endpoint pre-mocked."""
    # Token endpoint mock — always return a valid token
    httpx_mock.add_response(url=TOKEN_URL, method="POST", json=TOKEN_RESPONSE)
    return KeycloakAdminClient(
        keycloak_url=KC_URL,
        realm=REALM,
        client_id="admin-api-client",
        client_secret="test-secret",
    )


# ── 1-1: get_group ────────────────────────────────────────────────────────────


class TestGetGroup:
    """GET /groups/{id} → グループ情報（属性含む）を返す."""

    async def test_returns_group_with_attributes(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        group_data = {
            "id": "group-acme",
            "name": "acme-corp",
            "attributes": {
                "mfa_enabled": ["false"],
                "mfa_method": ["totp"],
            },
        }
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/group-acme",
            method="GET",
            json=group_data,
        )

        result = await kc.get_group("group-acme")

        assert result["id"] == "group-acme"
        assert result["name"] == "acme-corp"
        assert result["attributes"]["mfa_enabled"] == ["false"]
        assert result["attributes"]["mfa_method"] == ["totp"]

    async def test_raises_on_not_found(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/nonexistent",
            method="GET",
            status_code=404,
        )

        with pytest.raises(Exception):
            await kc.get_group("nonexistent")


# ── 1-2: update_group_attributes ──────────────────────────────────────────────


class TestUpdateGroupAttributes:
    """GET→PUT /groups/{id} で既存属性にマージして更新する."""

    async def test_merges_new_attributes_into_existing(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        existing_group = {
            "id": "group-acme",
            "name": "acme-corp",
            "path": "/acme-corp",
            "attributes": {
                "existing_key": ["existing_value"],
                "mfa_enabled": ["false"],
            },
        }
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/group-acme",
            method="GET",
            json=existing_group,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/group-acme",
            method="PUT",
            status_code=204,
        )

        await kc.update_group_attributes(
            "group-acme",
            {"mfa_enabled": ["true"], "mfa_method": ["totp"]},
        )

        # Verify the PUT payload merges attributes
        put_request = httpx_mock.get_requests()[-1]
        body = json.loads(put_request.content)
        assert body["attributes"]["existing_key"] == ["existing_value"]
        assert body["attributes"]["mfa_enabled"] == ["true"]
        assert body["attributes"]["mfa_method"] == ["totp"]

    async def test_creates_attributes_when_none_exist(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        existing_group = {
            "id": "group-new",
            "name": "new-corp",
            "path": "/new-corp",
        }
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/group-new",
            method="GET",
            json=existing_group,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/groups/group-new",
            method="PUT",
            status_code=204,
        )

        await kc.update_group_attributes(
            "group-new",
            {"mfa_enabled": ["true"]},
        )

        put_request = httpx_mock.get_requests()[-1]
        body = json.loads(put_request.content)
        assert body["attributes"]["mfa_enabled"] == ["true"]


# ── 1-3: set_user_attributes_bulk ─────────────────────────────────────────────


class TestSetUserAttributesBulk:
    """複数ユーザーの属性を一括更新。失敗したユーザーIDをリストで返す."""

    async def test_all_users_updated_successfully(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        user_ids = ["user-1", "user-2", "user-3"]

        # GET each user — return realistic Keycloak UserRepresentation
        for uid in user_ids:
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="GET",
                json={
                    "id": uid,
                    "username": f"{uid}@example.com",
                    "email": f"{uid}@example.com",
                    "enabled": True,
                    "attributes": {"tenant_id": ["acme-corp"]},
                },
            )
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="PUT",
                status_code=204,
            )

        failed = await kc.set_user_attributes_bulk(
            user_ids,
            {"mfa_enabled": ["true"], "mfa_method": ["totp"]},
        )

        assert failed == []

    async def test_put_sends_full_user_representation(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        """PUT body must include the complete UserRepresentation, not just attributes.

        Keycloak Admin API returns 400 Bad Request when required fields like
        'username' are missing from the PUT body.  This test ensures we send
        back the full object fetched via GET with the attributes merged in.
        """
        user_repr = {
            "id": "user-full",
            "username": "full@example.com",
            "email": "full@example.com",
            "firstName": "Full",
            "lastName": "User",
            "enabled": True,
            "emailVerified": True,
            "attributes": {"tenant_id": ["acme-corp"]},
        }
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-full",
            method="GET",
            json=user_repr,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-full",
            method="PUT",
            status_code=204,
        )

        await kc.set_user_attributes_bulk(
            ["user-full"],
            {"mfa_enabled": ["true"]},
        )

        put_request = [
            r for r in httpx_mock.get_requests() if r.method == "PUT"
        ][-1]
        body = json.loads(put_request.content)

        # Must include original fields — not just {"attributes": ...}
        assert body["id"] == "user-full"
        assert body["username"] == "full@example.com"
        assert body["email"] == "full@example.com"
        assert body["enabled"] is True
        # And merged attributes
        assert body["attributes"]["tenant_id"] == ["acme-corp"]
        assert body["attributes"]["mfa_enabled"] == ["true"]

    async def test_one_user_fails_returns_failed_list(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        # user-1: success, user-2: GET fails, user-3: success
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={"id": "user-1", "attributes": {"tenant_id": ["acme"]}},
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="PUT",
            status_code=204,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-2",
            method="GET",
            status_code=500,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-3",
            method="GET",
            json={"id": "user-3", "attributes": {"tenant_id": ["acme"]}},
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-3",
            method="PUT",
            status_code=204,
        )

        failed = await kc.set_user_attributes_bulk(
            ["user-1", "user-2", "user-3"],
            {"mfa_enabled": ["true"]},
        )

        assert failed == ["user-2"]

    async def test_empty_user_list_returns_empty(
        self, httpx_mock: HTTPXMock
    ) -> None:
        # No HTTP calls expected — create client without token mock
        client = KeycloakAdminClient(
            keycloak_url=KC_URL,
            realm=REALM,
            client_id="admin-api-client",
            client_secret="test-secret",
        )
        failed = await client.set_user_attributes_bulk([], {"mfa_enabled": ["true"]})
        assert failed == []

    async def test_merges_with_existing_attributes(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={
                "id": "user-1",
                "attributes": {
                    "tenant_id": ["acme-corp"],
                    "existing_attr": ["keep_me"],
                },
            },
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="PUT",
            status_code=204,
        )

        await kc.set_user_attributes_bulk(
            ["user-1"],
            {"mfa_enabled": ["true"]},
        )

        put_request = [
            r for r in httpx_mock.get_requests() if r.method == "PUT"
        ][-1]
        body = json.loads(put_request.content)
        assert body["attributes"]["tenant_id"] == ["acme-corp"]
        assert body["attributes"]["existing_attr"] == ["keep_me"]
        assert body["attributes"]["mfa_enabled"] == ["true"]


# ── 1-4: add_required_action_bulk ─────────────────────────────────────────────


class TestAddRequiredActionBulk:
    """複数ユーザーにrequiredActionを追加。重複なし."""

    async def test_adds_action_to_users(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        for uid in ["user-1", "user-2"]:
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="GET",
                json={
                    "id": uid,
                    "requiredActions": [],
                },
            )
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="PUT",
                status_code=204,
            )

        failed = await kc.add_required_action_bulk(
            ["user-1", "user-2"],
            "CONFIGURE_TOTP",
        )

        assert failed == []
        put_requests = [r for r in httpx_mock.get_requests() if r.method == "PUT"]
        for req in put_requests:
            body = json.loads(req.content)
            assert "CONFIGURE_TOTP" in body["requiredActions"]

    async def test_does_not_duplicate_existing_action(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={
                "id": "user-1",
                "requiredActions": ["CONFIGURE_TOTP"],
            },
        )
        # PUT should NOT be sent since action already exists

        failed = await kc.add_required_action_bulk(["user-1"], "CONFIGURE_TOTP")

        assert failed == []
        # Verify no PUT was issued (action already present → skip)
        put_requests = [r for r in httpx_mock.get_requests() if r.method == "PUT"]
        assert len(put_requests) == 0

    async def test_one_failure_returns_failed_list(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={"id": "user-1", "requiredActions": []},
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="PUT",
            status_code=204,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-2",
            method="GET",
            status_code=500,
        )

        failed = await kc.add_required_action_bulk(
            ["user-1", "user-2"],
            "CONFIGURE_TOTP",
        )

        assert failed == ["user-2"]


# ── 1-5: remove_required_action_bulk ──────────────────────────────────────────


class TestRemoveRequiredActionBulk:
    """複数ユーザーからrequiredActionを削除。存在しなければスキップ."""

    async def test_removes_action_from_users(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        for uid in ["user-1", "user-2"]:
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="GET",
                json={
                    "id": uid,
                    "requiredActions": ["CONFIGURE_TOTP", "VERIFY_EMAIL"],
                },
            )
            httpx_mock.add_response(
                url=f"{ADMIN_BASE}/users/{uid}",
                method="PUT",
                status_code=204,
            )

        failed = await kc.remove_required_action_bulk(
            ["user-1", "user-2"],
            "CONFIGURE_TOTP",
        )

        assert failed == []
        put_requests = [r for r in httpx_mock.get_requests() if r.method == "PUT"]
        for req in put_requests:
            body = json.loads(req.content)
            assert "CONFIGURE_TOTP" not in body["requiredActions"]
            assert "VERIFY_EMAIL" in body["requiredActions"]

    async def test_skips_when_action_not_present(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={
                "id": "user-1",
                "requiredActions": ["VERIFY_EMAIL"],
            },
        )
        # PUT should NOT be sent since CONFIGURE_TOTP is not present

        failed = await kc.remove_required_action_bulk(
            ["user-1"],
            "CONFIGURE_TOTP",
        )

        assert failed == []
        # Verify no PUT was issued (action absent → skip)
        put_requests = [r for r in httpx_mock.get_requests() if r.method == "PUT"]
        assert len(put_requests) == 0

    async def test_one_failure_returns_failed_list(
        self, kc: KeycloakAdminClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="GET",
            json={"id": "user-1", "requiredActions": ["CONFIGURE_TOTP"]},
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-1",
            method="PUT",
            status_code=204,
        )
        httpx_mock.add_response(
            url=f"{ADMIN_BASE}/users/user-2",
            method="GET",
            status_code=500,
        )

        failed = await kc.remove_required_action_bulk(
            ["user-1", "user-2"],
            "CONFIGURE_TOTP",
        )

        assert failed == ["user-2"]

    async def test_empty_user_list_returns_empty(
        self, httpx_mock: HTTPXMock
    ) -> None:
        # No HTTP calls expected — create client without token mock
        client = KeycloakAdminClient(
            keycloak_url=KC_URL,
            realm=REALM,
            client_id="admin-api-client",
            client_secret="test-secret",
        )
        failed = await client.remove_required_action_bulk([], "CONFIGURE_TOTP")
        assert failed == []
