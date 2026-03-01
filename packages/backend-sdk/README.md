# common-auth Backend SDK

Portable authentication SDK based on Keycloak and OIDC for FastAPI applications.

## Features

- **OIDC Authorization Code Flow + PKCE**: OAuth 2.1 recommended flow
- **JWT Verification**: RS256 signature verification with JWKS caching
- **Multi-tenant Support**: Row-Level Security (RLS) with PostgreSQL
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Graceful Degradation**: Continues authentication with cached JWKS when Keycloak is down
- **Developer-friendly**: Simple `setup_auth(app, config)` integration

## Installation

```bash
pip install common-auth
```

## Quick Start

### 1. Set Environment Variables

```bash
export KEYCLOAK_URL=https://keycloak.example.com
export KEYCLOAK_REALM=my-tenant
export KEYCLOAK_CLIENT_ID=my-app
```

### 2. Integrate with FastAPI

```python
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

# Setup authentication
config = AuthConfig.from_env()
setup_auth(app, config)

@app.get("/api/protected")
async def protected_endpoint(user: AuthUser = Depends(get_current_user)):
    return {"user_id": user.sub, "tenant": user.tenant_id}
```

### 3. Run Your App

```bash
uvicorn main:app --reload
```

## Configuration

### Required Environment Variables

| Variable | Description |
|---|---|
| `KEYCLOAK_URL` | Keycloak base URL |
| `KEYCLOAK_REALM` | Realm name |
| `KEYCLOAK_CLIENT_ID` | Client ID |

### Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TENANT_ID_SOURCE` | `iss` | How to extract tenant_id (`iss`, `custom`, `fixed`) |
| `TENANT_ID_CLAIM` | - | Custom JWT claim name (when `TENANT_ID_SOURCE=custom`) |
| `TENANT_ID_FIXED` | - | Fixed tenant ID (when `TENANT_ID_SOURCE=fixed`) |
| `JWKS_CACHE_TTL` | `86400` | JWKS cache TTL in seconds (24 hours) |
| `ENABLE_RLS` | `true` | Enable Row-Level Security session variable |
| `ENABLE_USER_SYNC` | `false` | Enable lazy sync to user_profiles table |

## Architecture

```
Request
   ↓
SecurityHeadersMiddleware  ← Add security headers
   ↓
JWTAuthMiddleware         ← Verify JWT, set request.state.user
   ↓
TenantMiddleware          ← SET LOCAL app.current_tenant_id
   ↓
Endpoint Handler
```

## API Endpoints

The SDK provides optional endpoints:

- `GET /auth/me` - Get current authenticated user info
- `GET /auth/health` - Check authentication service health
- `POST /auth/logout` - Logout (revoke tokens)

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Lint

```bash
ruff check .
mypy src
```

## License

Apache License 2.0
