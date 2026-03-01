# Auth Stack

Keycloak + PostgreSQL Docker Compose setup for common-auth development and testing.

## Quick Start

### 1. Copy Environment Variables

```bash
cp .env.example .env
```

Edit `.env` if you need to change default ports or credentials.

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Access Keycloak Admin Console

- URL: http://localhost:8080
- Username: `admin`
- Password: `admin`

### 4. Verify Realm Import

The `common-auth` realm should be automatically imported with:
- Client: `backend-app`
- Test Users:
  - `testuser@example.com` / `password123` (user role)
  - `admin@example.com` / `admin123` (admin role)

## Services

| Service | Port | Description |
|---|---|---|
| Keycloak | 8080 | Identity Provider |
| Keycloak DB | (internal) | PostgreSQL for Keycloak |
| App DB | 5433 | PostgreSQL for application (test/dev) |

## Application Database

The `app-db` service provides a PostgreSQL instance for testing with:
- Pre-created tables: `tenants`, `user_profiles`
- Row-Level Security enabled
- Sample tenant: `common-auth`

Connect:
```bash
psql -h localhost -p 5433 -U app_user -d app_db
```

## Health Checks

```bash
# Keycloak
curl http://localhost:8080/health/ready

# App DB
docker-compose exec app-db pg_isready -U app_user
```

## Stop Services

```bash
docker-compose down

# Remove volumes (reset databases)
docker-compose down -v
```

## Troubleshooting

### Keycloak takes long to start

First startup may take 1-2 minutes. Check logs:
```bash
docker-compose logs -f keycloak
```

### Realm not imported

Verify `keycloak/realm-export.json` exists and check logs:
```bash
docker-compose logs keycloak | grep -i import
```

### Port conflicts

Edit `.env` to change port numbers:
```bash
KEYCLOAK_PORT=9080
APP_DB_PORT=5434
```

## Phase 2 Features

### SMTP / Email

SMTP is required for password reset and email verification.
Set the `SMTP_*` variables in `.env` to enable.

Without SMTP configured, Keycloak will still start but email-dependent
features (password reset, email verification) will fail.

### MFA (TOTP)

MFA is pre-configured via `realm-export.json` with TOTP (6 digits, 30s period).
Users can optionally enrol via their Keycloak Account Console at
`http://localhost:8080/realms/common-auth/account/`.

To **require** MFA for all users, set `CONFIGURE_TOTP` as a
default required action in the Keycloak admin console.

### User Self-Registration

Self-registration is enabled by default (`registrationAllowed: true`).
Users register at the Keycloak login page.

### Rate Limiting

Rate limiting is applied by the Backend SDK middleware, not Keycloak.
Configure limits in `.env`:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=60    # per minute
RATE_LIMIT_LOGIN_REQUESTS=5       # per minute
```

## Development Workflow

1. Start Auth Stack: `docker-compose up -d`
2. Develop Backend SDK with hot reload
3. Test against running Keycloak
4. Stop: `docker-compose down`

## Production Deployment

This Docker Compose setup is for **development/testing only**.

For production:
- Use managed Keycloak (e.g., Keycloak Operator on Kubernetes)
- Use managed PostgreSQL (e.g., AWS RDS, Google Cloud SQL)
- Configure proper secrets management
- Enable HTTPS with valid certificates
- Review and harden security settings

See `docs/` for production deployment guidelines.
