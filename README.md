# common-auth

Portable authentication platform based on Keycloak and OIDC.

## 📋 Overview

common-auth provides a complete authentication solution for multi-project environments:

- **Auth Stack**: Keycloak + PostgreSQL (Docker Compose)
- **Backend SDK**: Python/FastAPI package for JWT verification
- **Frontend SDK**: React/TypeScript package (Coming in Phase 2)

### Key Features

- ✅ **Don't Roll Your Own Auth**: Uses Keycloak (proven OSS)
- ✅ **Portable**: Docker-based, works anywhere (AWS/Azure/GCP/On-prem)
- ✅ **Secure**: OIDC Authorization Code Flow + PKCE, RS256 JWT
- ✅ **Multi-tenant**: Row-Level Security (RLS) with PostgreSQL
- ✅ **Developer-friendly**: Simple `setup_auth(app, config)` integration
- ✅ **Production-ready**: Graceful degradation, caching, comprehensive error handling

## 🚀 Quick Start

### 1. Start Auth Stack

```bash
cd auth-stack
cp .env.example .env
docker-compose up -d
```

Wait for Keycloak to be ready (~1-2 minutes):
```bash
curl http://localhost:8080/health/ready
```

### 2. Install Backend SDK

```bash
cd packages/backend-sdk
pip install -e .
```

### 3. Create FastAPI App

```python
from fastapi import FastAPI, Depends
from common_auth import AuthConfig, setup_auth, get_current_user, AuthUser

app = FastAPI()

# Setup authentication
config = AuthConfig.from_env()
setup_auth(app, config)

@app.get("/api/protected")
async def protected(user: AuthUser = Depends(get_current_user)):
    return {"user_id": user.sub, "tenant": user.tenant_id}
```

### 4. Set Environment Variables

```bash
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=common-auth
export KEYCLOAK_CLIENT_ID=backend-app
```

### 5. Run and Test

```bash
uvicorn main:app --reload

# Get token
TOKEN=$(curl -X POST "http://localhost:8080/realms/common-auth/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=backend-app" \
  -d "username=testuser@example.com" \
  -d "password=password123" \
  | jq -r '.access_token')

# Access protected endpoint
curl http://localhost:8000/api/protected \
  -H "Authorization: Bearer $TOKEN"
```

## 📁 Project Structure

```
common-auth/
├── auth-stack/              # Keycloak + PostgreSQL
│   ├── docker-compose.yml
│   ├── keycloak/
│   │   └── realm-export.json
│   └── postgres/
│       └── init.sql
├── packages/
│   └── backend-sdk/         # Python SDK
│       ├── src/common_auth/
│       └── tests/
├── examples/
│   └── fastapi-app/         # Example application
└── docs/                    # Design documents
```

## 📚 Documentation

- [Backend SDK README](packages/backend-sdk/README.md)
- [Auth Stack README](auth-stack/README.md)
- [Example App README](examples/fastapi-app/README.md)
- [Design Documents](docs/)
  - [PRD](docs/prd/prd.md)
  - [API Specification](docs/api/openapi.yaml)
  - [DB Schema](docs/db/schema.sql)
  - [ADRs](docs/adr/)

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ OIDC Flow
       ▼
┌─────────────┐     JWKS      ┌─────────────┐
│  Keycloak   │◄──────────────┤ Backend SDK │
│   (Docker)  │               │  (FastAPI)  │
└──────┬──────┘               └──────┬──────┘
       │                             │
       ▼                             ▼
┌─────────────┐               ┌─────────────┐
│ Keycloak DB │               │  App DB     │
│(PostgreSQL) │               │(PostgreSQL) │
└─────────────┘               └─────────────┘
```

### Middleware Stack

```
Request
   ↓
SecurityHeadersMiddleware  ← Add security headers
   ↓
JWTAuthMiddleware         ← Verify JWT, set request.state.user
   ↓
TenantMiddleware          ← SET LOCAL app.current_tenant_id (RLS)
   ↓
Endpoint Handler
```

## 🧪 Testing

### Unit Tests

```bash
cd packages/backend-sdk
pytest tests/unit/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### E2E Tests

```bash
# Start Auth Stack first
cd auth-stack && docker-compose up -d
cd ../packages/backend-sdk
pytest tests/e2e/ -v
```

## 🔧 Development

### Setup Development Environment

```bash
# Backend SDK
cd packages/backend-sdk
pip install -e ".[dev]"

# Run linters
ruff check .
mypy src

# Run tests with coverage
pytest --cov=src/common_auth --cov-report=html
```

### Development Workflow

1. **Design** → `/design` command (5 experts discussion)
2. **Implementation Plan** → `/implement` command (TDD plan)
3. **Implementation** → TDD cycle (Red-Green-Refactor)
4. **Review** → `/review` command (5 experts review)
5. **Fix** → `/fix` command
6. **Re-review** → `/re-review` command
7. **Push** → `/push` command

## 🎯 Roadmap

### Phase 1 (MVP) ✅
- [x] Auth Stack (Keycloak + PostgreSQL)
- [x] Backend SDK (Python/FastAPI)
  - [x] JWT verification
  - [x] JWKS caching with graceful degradation
  - [x] Security headers middleware
  - [x] Row-Level Security support
  - [x] `/auth/me`, `/auth/health` endpoints
- [x] Example FastAPI application
- [x] Documentation

### Phase 2 (Next)
- [ ] MFA support
- [ ] Password reset flow
- [ ] User self-registration
- [ ] Rate limiting middleware
- [ ] Frontend SDK (React/TypeScript)

### Phase 3 (Future)
- [ ] Social login (Google, Microsoft)
- [ ] Audit logging
- [ ] Keycloak Admin API wrapper
- [ ] Multi-language support

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

Apache License 2.0

## 🔗 Related Projects

- [Keycloak](https://www.keycloak.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PyJWT](https://pyjwt.readthedocs.io/)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/common-auth/common-auth/issues)
- Discussions: [GitHub Discussions](https://github.com/common-auth/common-auth/discussions)
- Documentation: [docs/](docs/)
