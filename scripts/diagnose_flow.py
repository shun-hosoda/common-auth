"""フロー詳細診断 + OIDC authorization URLを生成してブラウザテスト用URLを表示"""
import urllib.request, urllib.parse, json

def get(url, t):
    r = urllib.request.Request(url, headers={'Authorization': f'Bearer {t}'})
    with urllib.request.urlopen(r) as resp: return json.loads(resp.read())

def post_form(url, data):
    b = urllib.parse.urlencode(data).encode()
    r = urllib.request.Request(url, data=b, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(r) as resp: return json.loads(resp.read())

BASE = "http://localhost:8080"
REALM = "common-auth"

t = post_form(f"{BASE}/realms/master/protocol/openid-connect/token",
              {"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"})["access_token"]
admin = f"{BASE}/admin/realms/{REALM}"

print("=== 1. フロー実行ツリー (優先度・設定付き) ===")
execs = get(f"{admin}/authentication/flows/unified-mfa-browser/executions", t)
for e in execs:
    indent = "  " * e.get("level", 0)
    cfg_str = ""
    if e.get("authenticationConfig"):
        try:
            c = get(f"{admin}/authentication/config/{e['authenticationConfig']}", t)
            cfg_str = f" → config={c.get('config', {})}"
        except Exception as ex:
            cfg_str = f" → config_err={ex}"
    print(f"{indent}[{e.get('requirement')}] {e.get('displayName')} idx={e.get('index')} {cfg_str}")

print()
print("=== 2. admin_acme-corp ユーザー属性 ===")
users = get(f"{admin}/users?username=admin_acme-corp%40example.com&exact=true", t)
u = users[0] if users else {}
print(f"  attributes: {u.get('attributes', {})}")
print(f"  requiredActions: {u.get('requiredActions', [])}")

creds = get(f"{admin}/users/{u['id']}/credentials", t)
print(f"  credentials: {[{'type': c.get('type'), 'id': c.get('id', '')[:8]} for c in creds]}")

print()
print("=== 3. クライアント example-app 設定 ===")
clients = get(f"{admin}/clients?clientId=example-app", t)
c = clients[0] if clients else {}
print(f"  directAccessGrantsEnabled: {c.get('directAccessGrantsEnabled')}")
print(f"  publicClient: {c.get('publicClient')}")
print(f"  authenticationFlowBindingOverrides: {c.get('authenticationFlowBindingOverrides', {})}")

print()
print("=== 4. Realm browserFlow ===")
realm = get(f"{admin}", t)
print(f"  browserFlow: {realm.get('browserFlow')}")

print()
print("=== 5. テスト用 authorization URL (ブラウザで開いてフロー確認) ===")
params = urllib.parse.urlencode({
    "client_id": "example-app",
    "redirect_uri": "http://localhost:3000/callback",
    "response_type": "code",
    "scope": "openid profile email",
    "prompt": "login",
    "nonce": "test123",
})
print(f"  {BASE}/realms/{REALM}/protocol/openid-connect/auth?{params}")

print()
print("=== 6. Realm level direct grant test (MFA bypass有無確認) ===")
print("  directGrantFlow:", realm.get("directGrantFlow"))
