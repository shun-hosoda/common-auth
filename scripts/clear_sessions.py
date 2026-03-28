"""Clear all active Keycloak SSO sessions so MFA is prompted on next login."""
import httpx

KC_URL = "http://localhost:8080"
REALM = "common-auth"


def main() -> None:
    tk = httpx.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": "admin", "password": "admin"},
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tk}"}

    users = httpx.get(
        f"{KC_URL}/admin/realms/{REALM}/users?max=50", headers=h
    ).json()

    total_cleared = 0
    for u in users:
        uid = u["id"]
        username = u["username"]
        sessions = httpx.get(
            f"{KC_URL}/admin/realms/{REALM}/users/{uid}/sessions", headers=h
        ).json()
        for s in sessions:
            r = httpx.delete(
                f"{KC_URL}/admin/realms/{REALM}/sessions/{s['id']}", headers=h
            )
            print(f"  Deleted session {s['id'][:8]} for {username}: {r.status_code}")
            total_cleared += 1

    # Verify
    print(f"\nTotal sessions cleared: {total_cleared}")
    for u in users:
        uid = u["id"]
        remaining = httpx.get(
            f"{KC_URL}/admin/realms/{REALM}/users/{uid}/sessions", headers=h
        ).json()
        status = "✅ no sessions" if not remaining else f"⚠️  {len(remaining)} still active"
        print(f"  {u['username']}: {status}")


if __name__ == "__main__":
    main()
