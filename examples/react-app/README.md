# Common Auth - React Example

React application demonstrating @common-auth/react SDK with Keycloak.

## Features

- Login with OIDC Authorization Code + PKCE
- Two-Factor Authentication (TOTP)
- Password Reset (email notification)
- User Self-Registration
- Dashboard with user profile and token info

## Prerequisites

1. Auth Stack running (Keycloak + PostgreSQL)
2. Frontend client registered in Keycloak

## Quick Start

### 1. Start Auth Stack

```bash
cd ../../auth-stack
cp .env.example .env
docker-compose up -d
```

Wait for Keycloak to start (~1-2 minutes):
```bash
curl http://localhost:8080/health/ready
```

### 2. Register Frontend Client in Keycloak

1. Open http://localhost:8080
2. Login with `admin` / `admin`
3. Select "common-auth" realm
4. Go to **Clients** → **Create client**
5. Configure:

| Setting | Value |
|---------|-------|
| Client ID | `frontend-app` |
| Client authentication | OFF |
| Valid redirect URIs | `http://localhost:3000/*` |
| Valid post logout redirect URIs | `http://localhost:3000/*` |
| Web origins | `http://localhost:3000` |

### 3. Install & Run

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Login Flow

1. Click **Login** → Redirects to Keycloak login page
2. Enter credentials: `testuser@example.com` / `password123`
3. (Optional) Enter TOTP code if MFA is enabled
4. Redirects back to `/callback` → `/dashboard`

## Password Reset Flow

1. Click **Forgot password?** → Redirects to Keycloak reset page
2. Enter email address
3. Check email for reset link (requires SMTP configured)
4. Click link → Set new password
5. Login with new password

## MFA Setup Flow

1. Login to dashboard
2. Click **Setup MFA** → Redirects to Keycloak account console
3. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
4. Enter verification code
5. MFA is now required on next login

## User Registration Flow

1. Click **Register** → Redirects to Keycloak registration page
2. Fill in email, password, name
3. (If email verification enabled) Check email for verification link
4. Login with new account

## Configuration

Edit `src/main.tsx` to change Keycloak settings:

```typescript
const AUTH_CONFIG = {
  authority: 'http://localhost:8080/realms/common-auth',
  clientId: 'frontend-app',
  redirectUri: 'http://localhost:3000/callback',
  postLogoutRedirectUri: 'http://localhost:3000',
}
```

## Troubleshooting

### "Invalid redirect_uri" error

Ensure the redirect URI in Keycloak client settings matches exactly:
- `http://localhost:3000/*` (with wildcard)

### CORS errors

Check Web Origins in Keycloak client settings:
- `http://localhost:3000`

### Password reset email not received

Configure SMTP in `auth-stack/.env`:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Then restart Auth Stack:
```bash
docker-compose down && docker-compose up -d
```
