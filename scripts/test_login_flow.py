"""Simulate browser login flow to test if OTP is prompted."""
import requests
from urllib.parse import urlencode, urlparse, parse_qs
import re
import hashlib
import base64
import os

session = requests.Session()

# Generate PKCE
code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode()
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b'=').decode()

# Step 1: Start auth flow with prompt=login
auth_url = "http://localhost:8080/realms/common-auth/protocol/openid-connect/auth"
params = {
    "client_id": "example-app",
    "redirect_uri": "http://localhost:3000/callback",
    "response_type": "code",
    "scope": "openid profile email",
    "prompt": "login",
    "nonce": "test123",
    "state": "test_state",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256"
}
print(f"Step 1: GET {auth_url}?{urlencode(params)}")
r1 = session.get(auth_url, params=params, allow_redirects=True)
print(f"  Status: {r1.status_code}")
print(f"  Final URL: {r1.url}")

# Check if we got a login form
if "action" in r1.text:
    # Find the form action URL
    action_match = re.search(r'action="([^"]+)"', r1.text)
    if action_match:
        action_url = action_match.group(1).replace("&amp;", "&")
        print(f"  Form action: {action_url}")
    else:
        print("  No form action found!")
        
    # Check what inputs are in the form
    inputs = re.findall(r'name="([^"]+)"', r1.text)
    print(f"  Form inputs: {inputs}")
    
    # Check if it's username/password form or OTP form
    if "username" in r1.text and "password" in r1.text:
        print("  -> Login form (username/password)")
        
        # Step 2: Submit credentials
        print(f"\nStep 2: POST credentials (admin_acme-corp@example.com / admin123)")
        r2 = session.post(action_url, data={
            "username": "admin_acme-corp@example.com",
            "password": "admin123"
        }, allow_redirects=False)
        print(f"  Status: {r2.status_code}")
        print(f"  Location: {r2.headers.get('Location', 'N/A')}")
        
        if r2.status_code == 302:
            location = r2.headers['Location']
            # Check if redirected to callback (= no OTP) or to another form
            if '/callback' in location:
                print("  ❌ REDIRECTED TO CALLBACK - NO OTP ASKED!")
                parsed = urlparse(location)
                qs = parse_qs(parsed.query)
                print(f"  code={qs.get('code', ['N/A'])[0][:20]}...")
            else:
                print(f"  -> Following redirect...")
                r3 = session.get(location, allow_redirects=True)
                print(f"  Status: {r3.status_code}")
                print(f"  Final URL: {r3.url}")
                
                if "otp" in r3.text.lower() or "totp" in r3.text.lower() or "authenticator" in r3.text.lower():
                    print("  ✅ OTP FORM SHOWN!")
                else:
                    # Check what form is shown
                    action_match2 = re.search(r'action="([^"]+)"', r3.text)
                    inputs2 = re.findall(r'name="([^"]+)"', r3.text)
                    print(f"  Form inputs: {inputs2}")
                    if "otp" in str(inputs2).lower():
                        print("  ✅ OTP FORM SHOWN!")
                    else:
                        print(f"  Page title/content sample:")
                        title = re.search(r'<title>([^<]+)</title>', r3.text)
                        if title:
                            print(f"    Title: {title.group(1)}")
                        # Print a portion of the page body
                        print(f"    Body snippet: {r3.text[500:1500]}")
        elif r2.status_code == 200:
            # Might be showing OTP form directly after password
            if "otp" in r2.text.lower() or "totp" in r2.text.lower():
                print("  ✅ OTP FORM SHOWN!")
            else:
                inputs2 = re.findall(r'name="([^"]+)"', r2.text)
                print(f"  Response form inputs: {inputs2}")
                print(f"  Checking for OTP keywords: 'otp' in text = {'otp' in r2.text.lower()}")
                title = re.search(r'<title>([^<]+)</title>', r2.text)
                if title:
                    print(f"  Title: {title.group(1)}")
    elif "otp" in r1.text.lower():
        print("  -> OTP form (already authenticated?)")
    else:
        print(f"  -> Unknown form. Inputs: {inputs}")
else:
    print("  No form in response.")
    # Check if we got redirected straight to callback
    if '/callback' in r1.url:
        print("  ❌ REDIRECTED TO CALLBACK WITHOUT LOGIN!")
