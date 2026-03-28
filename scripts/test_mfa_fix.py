"""MFA fix end-to-end verification script.

Verifies that PUT /api/admin/security/mfa correctly sets mfa_enabled
on all tenant users (regression test for partial-PUT bug).
"""
import asyncio
import json
import sys
import httpx

KC_URL = "http://localhost:8080"
REALM = "common-auth"
APP_URL = "http://localhost:8000"


async def main() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Keycloak admin token
        r = await client.post(
            f"{KC_URL}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli",
                  "username": "admin", "password": "admin"},
        )
        r.raise_for_status()
        tk = r.json()["access_token"]
        print("✅ admin token OK")

        # 2. Find admin_acme-corp user
        r = await client.get(
            f"{KC_URL}/admin/realms/{REALM}/users?max=50",
            headers={"Authorization": f"Bearer {tk}"},
        )
        r.raise_for_status()
        users = r.json()
        admin_user = next((u for u in users if u["username"] == "admin_acme-corp@example.com"), None)
        if not admin_user:
            print("❌ admin_acme-corp not found")
            sys.exit(1)
        aid = admin_user["id"]
        print(f"✅ admin_acme-corp id={aid}")

        # 3. Reset password + clear requiredActions
        r = await client.put(
            f"{KC_URL}/admin/realms/{REALM}/users/{aid}/reset-password",
            headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
            content=json.dumps({"type": "password", "value": "admin123", "temporary": False}),
        )
        r.raise_for_status()
        print("✅ password reset to admin123")

        full = (await client.get(
            f"{KC_URL}/admin/realms/{REALM}/users/{aid}",
            headers={"Authorization": f"Bearer {tk}"},
        )).json()
        full["requiredActions"] = []
        await client.put(
            f"{KC_URL}/admin/realms/{REALM}/users/{aid}",
            headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
            content=json.dumps(full),
        )
        print("✅ requiredActions cleared")

        # 4. Login as admin_acme-corp
        r = await client.post(
            f"{KC_URL}/realms/{REALM}/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "example-app",
                  "username": "admin_acme-corp@example.com", "password": "admin123"},
        )
        if r.status_code != 200:
            print(f"❌ login failed: {r.text}")
            sys.exit(1)
        ut = r.json()["access_token"]
        print("✅ admin_acme-corp login OK")

        # 5. PUT /api/admin/security/mfa (enable MFA)
        r = await client.put(
            f"{APP_URL}/api/admin/security/mfa",
            headers={"Authorization": f"Bearer {ut}", "Content-Type": "application/json"},
            content=json.dumps({"mfa_enabled": True, "mfa_method": "totp"}),
        )
        print(f"PUT /api/admin/security/mfa → {r.status_code}")
        if r.status_code != 200:
            print(f"❌ {r.text}")
            sys.exit(1)
        resp_data = r.json()
        print(f"   users_updated={resp_data.get('users_updated')} failed={resp_data.get('failed_users')}")

        # 6. Verify user attributes in Keycloak
        r = await client.get(
            f"{KC_URL}/admin/realms/{REALM}/users?max=50",
            headers={"Authorization": f"Bearer {tk}"},
        )
        r.raise_for_status()
        users_after = r.json()

        all_ok = True
        for u in users_after:
            if "acme-corp" not in u["username"]:
                continue
            attrs = (u.get("attributes") or {})
            mfa_enabled = attrs.get("mfa_enabled", ["(none)"])
            mfa_method = attrs.get("mfa_method", ["(none)"])
            actions = u.get("requiredActions", [])
            status = "✅" if mfa_enabled == ["true"] else "❌"
            if mfa_enabled != ["true"]:
                all_ok = False
            print(f"  {status} {u['username']}: mfa_enabled={mfa_enabled} mfa_method={mfa_method} actions={actions}")

        if all_ok:
            print("\n🎉 FIX VERIFIED: All acme-corp users have mfa_enabled=true")
        else:
            print("\n❌ FIX NOT WORKING: Some users still missing mfa_enabled")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
