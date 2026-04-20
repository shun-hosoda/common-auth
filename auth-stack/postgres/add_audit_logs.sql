-- audit_logs テーブル作成（手動適用用）
CREATE TABLE IF NOT EXISTS audit_logs (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID         NOT NULL REFERENCES tenants(id),
    actor_id      UUID         REFERENCES user_profiles(id) ON DELETE SET NULL,
    actor_email   VARCHAR(255),
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id   VARCHAR(255),
    details       JSONB        DEFAULT '{}',
    ip_address    INET,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id_created ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_action     ON audit_logs(tenant_id, action);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON audit_logs;
-- current_tenant_id が未設定の場合は NULLIF により NULL となり全行非表示（安全側フォールバック）
CREATE POLICY tenant_isolation_policy ON audit_logs
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);
