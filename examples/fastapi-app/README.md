# Common Auth Example Application

Example FastAPI application demonstrating common-auth SDK usage.

## Prerequisites

1. **Start Auth Stack** (Keycloak):
   ```bash
   cd ../../auth-stack
   cp .env.example .env
   docker-compose up -d
   ```

2. **Wait for Keycloak** to be ready (~1-2 minutes):
   ```bash
   curl http://localhost:8080/health/ready
   ```

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults should work with local Auth Stack).

## Run

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/auth/health

## Test Endpoints

### 1. Public Endpoint (No Auth)

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/public
```

### 2. Get Token from Keycloak

Using test user from realm-export.json:

```bash
# Get access token
TOKEN=$(curl -X POST "http://localhost:8080/realms/common-auth/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=backend-app" \
  -d "username=testuser@example.com" \
  -d "password=password123" \
  | jq -r '.access_token')

echo $TOKEN
```

### 3. Access Protected Endpoints

```bash
# Get user info
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Access protected endpoint
curl http://localhost:8000/api/protected \
  -H "Authorization: Bearer $TOKEN"

# Try admin endpoint (should fail with testuser)
curl http://localhost:8000/api/admin \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Test Admin Access

Get token for admin user:

```bash
ADMIN_TOKEN=$(curl -X POST "http://localhost:8080/realms/common-auth/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=backend-app" \
  -d "username=admin@example.com" \
  -d "password=admin123" \
  | jq -r '.access_token')

# Access admin endpoint
curl http://localhost:8000/api/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Available Endpoints

| Endpoint | Auth | Description |
|---|---|---|
| `GET /` | No | Root endpoint |
| `GET /api/public` | Optional | Public endpoint (shows user if authenticated) |
| `GET /api/protected` | Yes | Protected endpoint |
| `GET /api/admin` | Yes + Admin role | Admin-only endpoint |
| `GET /auth/me` | Yes | Get current user info |
| `GET /auth/health` | No | Auth service health check |
| `POST /auth/logout` | Yes | Logout |

## Test Users

From `auth-stack/keycloak/realm-export.json`:

| Email | Password | Roles |
|---|---|---|
| testuser@example.com | password123 | user |
| admin@example.com | admin123 | user, admin |

## Troubleshooting

### "Failed to fetch JWKS"

- Ensure Keycloak is running: `docker ps`
- Check Keycloak is healthy: `curl http://localhost:8080/health/ready`
- Verify KEYCLOAK_URL in `.env`

### "Invalid token"

- Token may have expired (5 minute lifetime)
- Verify KEYCLOAK_REALM matches in `.env` and token request
- Check token signature with jwt.io

### "Authentication service error"

- Check environment variables are set correctly
- Review application logs for details

## Development

### Hot Reload

The app runs with `reload=True`, so code changes trigger automatic restart.

### Logging

Logs show:
- Authentication events (user login)
- Token verification
- JWKS fetches
- Errors

## Next Steps

- Add database integration (SQLAlchemy)
- Implement Lazy Sync to `user_profiles`
- Add RLS enforcement with `set_tenant_context()`
- Create integration tests

See `../../packages/backend-sdk/README.md` for more SDK documentation.
