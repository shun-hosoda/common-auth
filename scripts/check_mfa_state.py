"""Check current MFA state of all users and Keycloak flow config."""
import httpx
import json

KC_URL = "http://localhost:8080"
REALM = "common-auth"


def main() -> None:
    tk = httpx.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": "admin", "password": "admin"},
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tk}"}

    # 1. User attributes
    print("=== User mfa attributes ===")
    users = httpx.get(f"{KC_URL}/admin/realms/{REALM}/users?max=50", headers=h).json()
    for u in users:
        attrs = u.get("attributes") or {}
        mfa_e = attrs.get("mfa_enabled", ["(none)"])
        mfa_m = attrs.get("mfa_method", ["(none)"])
        actions = u.get("requiredActions", [])
        totp = u.get("totp", False)
        print(f"  {u['username']}: mfa_enabled={mfa_e} mfa_method={mfa_m} actions={actions} totp={totp}")

    # 2. Browser flow
    print("\n=== Realm browserFlow ===")
    realm = httpx.get(f"{KC_URL}/admin/realms/{REALM}", headers=h).json()
    print(f"  browserFlow: {realm.get('browserFlow')}")

    # 3. Flow executions for unified-mfa-browser
    print("\n=== unified-mfa-browser executions ===")
    flows = httpx.get(f"{KC_URL}/admin/realms/{REALM}/authentication/flows", headers=h).json()
    mfa_flow = next((f for f in flows if f["alias"] == "unified-mfa-browser"), None)
    if mfa_flow:
        execs = httpx.get(
            f"{KC_URL}/admin/realms/{REALM}/authentication/flows/unified-mfa-browser/executions",
            headers=h,
        ).json()
        for e in execs:
            print(f"  [{e.get('requirement')}] {e.get('displayName') or e.get('providerId')} id={e.get('id')} authExec={e.get('authenticationConfig')}")
    else:
        print("  unified-mfa-browser flow NOT FOUND")

    # 4. Condition configs
    print("\n=== Condition configs ===")
    if mfa_flow:
        for e in execs:
            cfg_id = e.get("authenticationConfig")
            if cfg_id:
                cfg = httpx.get(
                    f"{KC_URL}/admin/realms/{REALM}/authentication/config/{cfg_id}",
                    headers=h,
                ).json()
                print(f"  {e.get('displayName') or e.get('providerId')}: {json.dumps(cfg.get('config', {}))}")


    # 5. Active sessions for admin_acme-corp
    print("\n=== admin_acme-corp active sessions ===")
    users2 = httpx.get(f"{KC_URL}/admin/realms/{REALM}/users?search=admin_acme-corp&max=5", headers=h).json()
    if users2:
        uid = users2[0]["id"]
        sessions = httpx.get(f"{KC_URL}/admin/realms/{REALM}/users/{uid}/sessions", headers=h).json()
        print(f"  Active SSO sessions: {len(sessions)}")
        for s in sessions:
            clients = list(s.get("clients", {}).values())
            print(f"    id={s.get('id')[:8]} start={s.get('start')} clients={clients}")

    # 6. Realm flows
    print("\n=== Realm flow bindings ===")
    realm2 = httpx.get(f"{KC_URL}/admin/realms/{REALM}", headers=h).json()
    print(f"  browserFlow:     {realm2.get('browserFlow')}")
    print(f"  directGrantFlow: {realm2.get('directGrantFlow')}")


if __name__ == "__main__":
    main()
