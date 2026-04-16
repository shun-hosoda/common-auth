"""Test MFA browser flow simulation with PKCE."""
import hashlib
import base64
import os
import re

import httpx


def main():
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()

    client = httpx.Client(follow_redirects=False, timeout=10, cookies=httpx.Cookies())

    auth_url = (
        f"http://localhost:8080/realms/common-auth/protocol/openid-connect/auth"
        f"?client_id=example-app"
        f"&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback"
        f"&response_type=code&scope=openid"
        f"&code_challenge={challenge}&code_challenge_method=S256"
    )

    def get_login_form():
        nonlocal client
        # Fresh client per login attempt to ensure clean cookie state
        client = httpx.Client(follow_redirects=False, timeout=10)
        verifier_new = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
        challenge_new = base64.urlsafe_b64encode(
            hashlib.sha256(verifier_new.encode()).digest()
        ).rstrip(b"=").decode()
        url = (
            f"http://127.0.0.1:8080/realms/common-auth/protocol/openid-connect/auth"
            f"?client_id=example-app"
            f"&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback"
            f"&response_type=code&scope=openid"
            f"&code_challenge={challenge_new}&code_challenge_method=S256"
        )
        r = client.get(url)
        if r.status_code == 302:
            r = client.get(r.headers["location"])
        match = re.search(r'action="([^"]+)"', r.text)
        return match.group(1).replace("&amp;", "&") if match else None

    # Test 1: admin_acme-corp (MFA enabled + OTP configured)
    print("=== admin_acme-corp (MFA=true, OTP=configured) ===")
    form_action = get_login_form()
    r2 = client.post(form_action, data={"username": "admin_acme-corp@example.com", "password": "admin123"}, follow_redirects=False)
    print(f"  Status: {r2.status_code}")
    if r2.status_code == 400:
        print(f"  Body: {r2.text[:500]}")
        # Try extracting error message
        err_match = re.search(r'id="kc-error-message"[^>]*>(.*?)</div>', r2.text, re.DOTALL)
        if err_match:
            print(f"  KC Error: {err_match.group(1).strip()}")
        err_match2 = re.search(r'class="alert[^"]*"[^>]*>(.*?)</span>', r2.text, re.DOTALL)
        if err_match2:
            print(f"  Alert: {err_match2.group(1).strip()}")
    if r2.status_code == 200:
        t = r2.text.lower()
        if "otp" in t or "authenticator" in t:
            print("  >>> OTP FORM DETECTED! MFA working!")
        else:
            inputs = re.findall(r'name="([^"]+)"', r2.text)
            print(f"  Form inputs: {inputs}")
    elif r2.status_code == 302:
        loc = r2.headers.get("location", "")
        print(f"  Redirect: {loc[:100]}")
        if "code=" in loc:
            print("  >>> NO MFA! REDIRECTED TO CALLBACK!")

    # Test 2: testuser_acme-corp (MFA enabled + OTP NOT configured)
    print("\n=== testuser_acme-corp (MFA=true, OTP=not configured) ===")
    form_action = get_login_form()
    r3 = client.post(form_action, data={"username": "testuser_acme-corp@example.com", "password": "password123"}, follow_redirects=False)
    print(f"  Status: {r3.status_code}")
    if r3.status_code == 200:
        t = r3.text.lower()
        if "otp" in t:
            print("  >>> OTP/CONFIGURE form detected!")
        else:
            inputs = re.findall(r'name="([^"]+)"', r3.text)
            print(f"  Form inputs: {inputs}")
    elif r3.status_code == 302:
        loc = r3.headers.get("location", "")
        print(f"  Redirect: {loc[:100]}")

    # Test 3: testuser_globex-inc (MFA DISABLED)
    print("\n=== testuser_globex-inc (MFA=false) ===")
    form_action = get_login_form()
    r4 = client.post(form_action, data={"username": "testuser_globex-inc@example.com", "password": "password123"}, follow_redirects=False)
    print(f"  Status: {r4.status_code}")
    if r4.status_code == 302:
        loc = r4.headers.get("location", "")
        if "code=" in loc:
            print("  >>> No MFA, direct callback (expected!)")
        else:
            print(f"  Redirect: {loc[:100]}")
    elif r4.status_code == 200:
        inputs = re.findall(r'name="([^"]+)"', r4.text)
        print(f"  Form inputs: {inputs}")


if __name__ == "__main__":
    main()
