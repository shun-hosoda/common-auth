"""
MFA フローを修正するスクリプト (stdlib only).
"""
import urllib.request, urllib.parse, json, sys

BASE = "http://localhost:8080"
REALM = "common-auth"

def req(method, url, *, data=None, token=None):
    if token:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = json.dumps(data).encode() if data is not None else None
    else:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = urllib.parse.urlencode(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {raw.decode()[:300]}")

def get_token():
    _, d = req("POST", f"{BASE}/realms/master/protocol/openid-connect/token",
               data={"grant_type":"password","client_id":"admin-cli","username":"admin","password":"admin"})
    return d["access_token"]

def aget(t, p): _, d = req("GET", f"{BASE}/admin/realms/{REALM}{p}", token=t); return d
def apost(t, p, d):
    # URL-encode path segments (handles spaces in flow aliases)
    enc = urllib.parse.quote(p, safe="/:?=&")
    return req("POST", f"{BASE}/admin/realms/{REALM}{enc}", data=d, token=t)
def aput(t, p, d): s, _ = req("PUT", f"{BASE}/admin/realms/{REALM}{p}", data=d, token=t); return s
def adel(t, p):
    try: s, _ = req("DELETE", f"{BASE}/admin/realms/{REALM}{p}", token=t); return s
    except RuntimeError as e:
        if "404" in str(e): return 404
        raise

def main():
    print("=== MFA フロー修正 ===")
    t = get_token()
    execs = aget(t, "/authentication/flows/unified-mfa-browser/executions")
    print("\n[現在の構造]")
    for e in execs:
        print("  "*e.get("level",0) + f"[{e.get('requirement')}] {e.get('displayName')} id={e.get('id','?')} prov={e.get('providerId','')}")

    mfa_gate   = next((e for e in execs if "mfa-gate"      in (e.get("displayName") or "")), None)
    totp_sub   = next((e for e in execs if "totp-subflow"  in (e.get("displayName") or "")), None)

    if not mfa_gate:
        print("ERR: mfa-gate not found"); sys.exit(1)

    if not totp_sub:
        otp_l2 = next((e for e in execs if e.get("level")==2 and e.get("providerId")=="auth-otp-form"), None)
        if otp_l2:
            print("Already flat. Done.")
        else:
            print("ERR: totp-subflow not found and OTP not at level 2"); sys.exit(1)
        return

    gfid = mfa_gate["flowId"]
    print(f"\nmfa-gate flowId: {gfid}")

    # flowId を alias に変換（Keycloak API は alias でフローを指定する）
    gate_flow = aget(t, f"/authentication/flows/{gfid}")
    gate_alias = gate_flow["alias"]   # e.g. "unified-mfa-browser mfa-gate"
    print(f"mfa-gate alias: {gate_alias}")

    # 1. Add mfa_method condition to mfa-gate
    print("[1] mfa_method 条件追加...")
    apost(t, f"/authentication/flows/{gate_alias}/executions/execution", {"provider":"conditional-user-attribute"})
    e2 = aget(t, "/authentication/flows/unified-mfa-browser/executions")
    old_ids = {e["id"] for e in execs if e.get("level")==2 and e.get("providerId")=="conditional-user-attribute"}
    nc = next((e for e in e2 if e.get("level")==2 and e.get("providerId")=="conditional-user-attribute" and e["id"] not in old_ids), None)
    if not nc: print("ERR: new condition not found"); sys.exit(1)
    print(f"   new condition: {nc['id']}")

    # 2. Configure it
    print("[2] mfa_method==totp 設定...")
    apost(t, f"/authentication/executions/{nc['id']}/config", {"alias":"mfa-method-totp","config":{"attribute_name":"mfa_method","not":"false","expected_attribute_value":"totp"}})

    # 3. Set REQUIRED
    print("[3] REQUIRED に設定...")
    upd = dict(nc); upd["requirement"] = "REQUIRED"
    aput(t, "/authentication/flows/unified-mfa-browser/executions", upd)

    # 4. Add OTP Form to mfa-gate
    print("[4] OTP Form 追加...")
    apost(t, f"/authentication/flows/{gate_alias}/executions/execution", {"provider":"auth-otp-form"})
    e3 = aget(t, "/authentication/flows/unified-mfa-browser/executions")
    old_otp = {e["id"] for e in execs if e.get("providerId")=="auth-otp-form"}
    no = next((e for e in e3 if e.get("providerId")=="auth-otp-form" and e["id"] not in old_otp), None)
    if not no: print("ERR: new OTP Form not found"); sys.exit(1)
    print(f"   new OTP Form: {no['id']}")

    # 5. Set OTP REQUIRED
    print("[5] OTP Form を REQUIRED に...")
    upd2 = dict(no); upd2["requirement"] = "REQUIRED"
    aput(t, "/authentication/flows/unified-mfa-browser/executions", upd2)

    # 6. Delete totp-subflow (cascade deletes its children)
    print(f"[6] totp-subflow 削除... id={totp_sub['id']}")
    s = adel(t, f"/authentication/executions/{totp_sub['id']}")
    print(f"   -> {s}")

    # Final
    print("\n[修正後の構造]")
    ef = aget(t, "/authentication/flows/unified-mfa-browser/executions")
    for e in ef:
        print("  "*e.get("level",0) + f"[{e.get('requirement')}] {e.get('displayName')} prov={e.get('providerId','')}")

    # Clear active sessions
    print("\n[セッションクリア]")
    for u in aget(t, "/users?search=acme-corp"):
        ss = aget(t, f"/users/{u['id']}/sessions")
        for s in ss:
            adel(t, f"/sessions/{s['id']}")
            print(f"  Deleted session for {u.get('username','?')[:30]}")

    print("\n✅ 完了!")

if __name__ == "__main__":
    main()
