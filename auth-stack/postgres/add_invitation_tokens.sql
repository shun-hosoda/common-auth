-- invitation_tokens テーブル作成（手動適用用）
CREATE TABLE IF NOT EXISTS invitation_tokens (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID         NOT NULL REFERENCES tenants(id)           ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    token           VARCHAR(128) NOT NULL UNIQUE,
    role            VARCHAR(50)  NOT NULL DEFAULT 'user'
                                 CHECK (role IN ('user', 'tenant_admin')),
    group_id        UUID         REFERENCES tenant_groups(id)              ON DELETE SET NULL,
    invited_by      UUID         REFERENCES user_profiles(id)              ON DELETE SET NULL,
    custom_message  TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending', 'accepted', 'revoked')),
    expires_at      TIMESTAMPTZ  NOT NULL,
    accepted_at     TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    revoked_by      UUID         REFERENCES user_profiles(id)              ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitation_tokens_tenant_id ON invitation_tokens(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_token     ON invitation_tokens(token);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_email     ON invitation_tokens(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_status    ON invitation_tokens(status, expires_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_invitation_pending
    ON invitation_tokens(tenant_id, email)
    WHERE status = 'pending';

ALTER TABLE invitation_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON invitation_tokens;
CREATE POLICY tenant_isolation_policy ON invitation_tokens
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);
