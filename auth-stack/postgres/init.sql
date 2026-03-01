-- =============================================================
-- Application DB Initialization Script
-- =============================================================
-- This script creates the tenants and user_profiles tables
-- based on docs/db/schema.sql
-- =============================================================

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    realm_name      VARCHAR(100)  NOT NULL UNIQUE,
    display_name    VARCHAR(200)  NOT NULL,
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    settings        JSONB         DEFAULT '{}',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_realm_name ON tenants(realm_name);

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id              UUID          PRIMARY KEY,
    tenant_id       UUID          NOT NULL REFERENCES tenants(id),
    email           VARCHAR(255)  NOT NULL,
    email_verified  BOOLEAN       NOT NULL DEFAULT FALSE,
    display_name    VARCHAR(200),
    roles           TEXT[]        DEFAULT '{}',
    last_login_at   TIMESTAMPTZ,
    synced_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profiles_tenant_email ON user_profiles(tenant_id, email);

-- Enable Row-Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
DROP POLICY IF EXISTS tenant_isolation_policy ON user_profiles;
CREATE POLICY tenant_isolation_policy ON user_profiles
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

-- Insert sample tenant for testing
INSERT INTO tenants (id, realm_name, display_name) 
VALUES ('00000000-0000-0000-0000-000000000001', 'common-auth', 'Common Auth Test Tenant')
ON CONFLICT (realm_name) DO NOTHING;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Application database initialized successfully';
    RAISE NOTICE 'Tables created: tenants, user_profiles';
    RAISE NOTICE 'Row-Level Security enabled on user_profiles';
END $$;
