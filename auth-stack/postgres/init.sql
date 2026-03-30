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
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- 拡張プロフィール（docs/design/user-group-permission.md 参照）
    avatar_url      VARCHAR(500),
    phone_number    VARCHAR(50),
    job_title       VARCHAR(200),
    locale          VARCHAR(10)   DEFAULT 'ja',
    timezone        VARCHAR(50)   DEFAULT 'Asia/Tokyo',
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    deactivated_at  TIMESTAMPTZ,
    metadata        JSONB         DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profiles_tenant_email ON user_profiles(tenant_id, email);

-- Enable Row-Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
DROP POLICY IF EXISTS tenant_isolation_policy ON user_profiles;
CREATE POLICY tenant_isolation_policy ON user_profiles
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- テストテナント（common-auth / acme-corp / globex-inc）
INSERT INTO tenants (id, realm_name, display_name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'common-auth', 'Common Auth Test Tenant'),
    ('00000000-0000-0000-0000-000000000002', 'acme-corp',   'Acme Corp'),
    ('00000000-0000-0000-0000-000000000003', 'globex-inc',  'Globex Inc')
ON CONFLICT (realm_name) DO NOTHING;

-- =============================================================
-- グループ・権限管理テーブル（docs/design/user-group-permission.md 参照）
-- =============================================================

-- updated_at 自動更新トリガー関数
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- updated_at トリガー（user_profiles）
DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- テナント内グループ（部署・チーム等）
-- NOTE: PostgreSQL予約語 "groups" を避けるため tenant_groups と命名
CREATE TABLE IF NOT EXISTS tenant_groups (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID         NOT NULL REFERENCES tenants(id),
    name              VARCHAR(200) NOT NULL,
    description       TEXT,
    parent_group_id   UUID         REFERENCES tenant_groups(id) ON DELETE SET NULL,
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order        INTEGER      NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tg_no_self_ref CHECK (parent_group_id IS DISTINCT FROM id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tg_tenant_name_active
    ON tenant_groups (tenant_id, name) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_tg_tenant_id       ON tenant_groups(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tg_parent_group_id ON tenant_groups(parent_group_id);

DROP TRIGGER IF EXISTS trg_tenant_groups_updated_at ON tenant_groups;
CREATE TRIGGER trg_tenant_groups_updated_at
    BEFORE UPDATE ON tenant_groups
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

ALTER TABLE tenant_groups ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tenant_groups;
CREATE POLICY tenant_isolation ON tenant_groups
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- ユーザーとグループの多対多中間テーブル
CREATE TABLE IF NOT EXISTS user_group_memberships (
    user_id     UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    group_id    UUID        NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    added_by    UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_ugm_user_id  ON user_group_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_ugm_group_id ON user_group_memberships(group_id);

ALTER TABLE user_group_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_group_memberships;
CREATE POLICY tenant_isolation ON user_group_memberships
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- 権限定義テーブル（resource × action）
CREATE TABLE IF NOT EXISTS permissions (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID         REFERENCES tenants(id) ON DELETE CASCADE,
    resource     VARCHAR(100) NOT NULL,
    action       VARCHAR(50)  NOT NULL,
    description  TEXT,
    is_system    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_permissions_system_tenant
        CHECK (
            (is_system = TRUE  AND tenant_id IS NULL)
            OR
            (is_system = FALSE AND tenant_id IS NOT NULL)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_perm_system_resource_action
    ON permissions (resource, action) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_perm_tenant_resource_action
    ON permissions (tenant_id, resource, action) WHERE tenant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_permissions_tenant_id ON permissions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_permissions_resource   ON permissions(resource);

ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON permissions;
CREATE POLICY tenant_isolation ON permissions
    USING (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

-- グループへの権限割り当て
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id       UUID        NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    permission_id  UUID        NOT NULL REFERENCES permissions(id)   ON DELETE CASCADE,
    granted        BOOLEAN     NOT NULL DEFAULT TRUE,
    granted_by     UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,
    PRIMARY KEY (group_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_gp_group_id      ON group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_gp_permission_id ON group_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_gp_expires_at    ON group_permissions(expires_at) WHERE expires_at IS NOT NULL;

ALTER TABLE group_permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON group_permissions;
CREATE POLICY tenant_isolation ON group_permissions
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- ユーザーへの直接権限割り当て（グループ権限より優先）
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id        UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    permission_id  UUID        NOT NULL REFERENCES permissions(id)   ON DELETE CASCADE,
    granted        BOOLEAN     NOT NULL DEFAULT TRUE,
    granted_by     UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_up_user_id       ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_up_permission_id ON user_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_up_expires_at    ON user_permissions(expires_at) WHERE expires_at IS NOT NULL;

ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_permissions;
CREATE POLICY tenant_isolation ON user_permissions
    USING (
        user_id IN (
            SELECT id FROM user_profiles
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- システム共通権限プリセット
INSERT INTO permissions (tenant_id, resource, action, description, is_system) VALUES
    (NULL, 'users',    'read',   'ユーザー一覧・詳細の参照',                  TRUE),
    (NULL, 'users',    'write',  'ユーザーの作成・編集',                      TRUE),
    (NULL, 'users',    'delete', 'ユーザーの削除',                            TRUE),
    (NULL, 'users',    'admin',  'MFAリセット・パスワードリセット等の管理操作', TRUE),
    (NULL, 'groups',   'read',   'グループ一覧・詳細の参照',                  TRUE),
    (NULL, 'groups',   'write',  'グループの作成・編集',                      TRUE),
    (NULL, 'groups',   'admin',  'グループメンバーの管理',                    TRUE),
    (NULL, 'reports',  'read',   'レポートの参照',                            TRUE),
    (NULL, 'reports',  'export', 'レポートのエクスポート',                    TRUE),
    (NULL, 'billing',  'read',   '請求情報の参照',                            TRUE),
    (NULL, 'billing',  'admin',  '請求設定の変更',                            TRUE),
    (NULL, 'settings', 'read',   'テナント設定の参照',                        TRUE),
    (NULL, 'settings', 'write',  'テナント設定の変更',                        TRUE)
ON CONFLICT (resource, action) WHERE tenant_id IS NULL DO NOTHING;

-- 実効権限ビュー
CREATE OR REPLACE VIEW v_user_effective_permissions AS
SELECT
    up.user_id,
    p.tenant_id,
    p.resource,
    p.action,
    up.granted,
    'direct' AS source
FROM user_permissions up
JOIN permissions p ON p.id = up.permission_id
WHERE (up.expires_at IS NULL OR up.expires_at > NOW())

UNION ALL

SELECT
    ugm.user_id,
    p.tenant_id,
    p.resource,
    p.action,
    BOOL_AND(gp.granted) AS granted,
    'group' AS source
FROM user_group_memberships ugm
JOIN tenant_groups tg ON tg.id = ugm.group_id AND tg.is_active = TRUE
JOIN group_permissions gp ON gp.group_id = ugm.group_id
JOIN permissions p ON p.id = gp.permission_id
WHERE (gp.expires_at IS NULL OR gp.expires_at > NOW())
  AND NOT EXISTS (
    SELECT 1 FROM user_permissions up2
    WHERE up2.user_id = ugm.user_id
      AND up2.permission_id = gp.permission_id
      AND (up2.expires_at IS NULL OR up2.expires_at > NOW())
)
GROUP BY ugm.user_id, p.tenant_id, p.resource, p.action;

-- =============================================================
-- テストデータ: グループ
-- =============================================================

-- acme-corp のグループ
INSERT INTO tenant_groups (id, tenant_id, name, description, sort_order) VALUES
    ('10000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000002',
     '管理部', 'テナント管理・総務', 1),
    ('10000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000002',
     '開発チーム', 'プロダクト開発・エンジニアリング', 2),
    ('10000000-0000-0000-0000-000000000003',
     '00000000-0000-0000-0000-000000000002',
     '営業部', '営業・カスタマーサクセス', 3)
ON CONFLICT (id) DO NOTHING;

-- globex-inc のグループ
INSERT INTO tenant_groups (id, tenant_id, name, description, sort_order) VALUES
    ('10000000-0000-0000-0000-000000000011',
     '00000000-0000-0000-0000-000000000003',
     '管理部', 'テナント管理・総務', 1),
    ('10000000-0000-0000-0000-000000000012',
     '00000000-0000-0000-0000-000000000003',
     '開発チーム', 'プロダクト開発・エンジニアリング', 2),
    ('10000000-0000-0000-0000-000000000013',
     '00000000-0000-0000-0000-000000000003',
     '営業部', '営業・カスタマーサクセス', 3)
ON CONFLICT (id) DO NOTHING;

-- =============================================================
-- テストデータ: グループ権限
-- 管理部 → 全権限、開発チーム → users/reports 参照のみ
-- =============================================================
INSERT INTO group_permissions (group_id, permission_id)
    SELECT '10000000-0000-0000-0000-000000000001', id FROM permissions WHERE tenant_id IS NULL
ON CONFLICT (group_id, permission_id) DO NOTHING;

INSERT INTO group_permissions (group_id, permission_id)
    SELECT '10000000-0000-0000-0000-000000000011', id FROM permissions WHERE tenant_id IS NULL
ON CONFLICT (group_id, permission_id) DO NOTHING;

INSERT INTO group_permissions (group_id, permission_id)
    SELECT '10000000-0000-0000-0000-000000000002', id
    FROM permissions WHERE tenant_id IS NULL AND resource IN ('users', 'reports') AND action = 'read'
ON CONFLICT (group_id, permission_id) DO NOTHING;

INSERT INTO group_permissions (group_id, permission_id)
    SELECT '10000000-0000-0000-0000-000000000012', id
    FROM permissions WHERE tenant_id IS NULL AND resource IN ('users', 'reports') AND action = 'read'
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- =============================================================
-- テストデータ: ユーザー⇔グループ紐付け
-- NOTE: user_profiles は Keycloak ログイン時に Lazy Sync されるため、
--       初回 Docker 起動時は 0 行 INSERT になる（エラーにはならない）。
--       下記トリガー (trg_auto_assign_test_groups) により、
--       ユーザーが初回ログインして user_profiles が INSERT された時点で
--       自動的にグループへ紐付けられる。
-- =============================================================

-- テスト用自動グループ割り当てトリガー関数
-- ⚠️  WARNING: TEST-ONLY FUNCTION. DO NOT APPLY TO PRODUCTION.
--              email プレフィックスでグループ割り当てを決定するのは
--              本番環境におけるアンチパターンです。
--              本番DBへのマイグレーション時はこの関数を含めないこと。
CREATE OR REPLACE FUNCTION fn_auto_assign_test_groups()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- acme-corp: admin系 → 管理部、それ以外 → 開発チーム
    IF NEW.tenant_id = '00000000-0000-0000-0000-000000000002' THEN
        IF NEW.email LIKE 'admin_%' THEN
            INSERT INTO user_group_memberships (user_id, group_id)
            VALUES (NEW.id, '10000000-0000-0000-0000-000000000001')
            ON CONFLICT (user_id, group_id) DO NOTHING;
        ELSE
            INSERT INTO user_group_memberships (user_id, group_id)
            VALUES (NEW.id, '10000000-0000-0000-0000-000000000002')
            ON CONFLICT (user_id, group_id) DO NOTHING;
        END IF;
    -- globex-inc: admin系 → 管理部、それ以外 → 営業部
    ELSIF NEW.tenant_id = '00000000-0000-0000-0000-000000000003' THEN
        IF NEW.email LIKE 'admin_%' THEN
            INSERT INTO user_group_memberships (user_id, group_id)
            VALUES (NEW.id, '10000000-0000-0000-0000-000000000011')
            ON CONFLICT (user_id, group_id) DO NOTHING;
        ELSE
            INSERT INTO user_group_memberships (user_id, group_id)
            VALUES (NEW.id, '10000000-0000-0000-0000-000000000013')
            ON CONFLICT (user_id, group_id) DO NOTHING;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auto_assign_test_groups ON user_profiles;
CREATE TRIGGER trg_auto_assign_test_groups
    AFTER INSERT ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION fn_auto_assign_test_groups();

-- 既存 user_profiles に対して手動で実行（再起動後に残っていた場合の補完）
-- NOTE: docker-compose down -v 後の初回起動時は user_profiles が空のため
--       以下の INSERT は 0行になる（エラーにはならない）。
--       データが残っている場合（ボリューム保持）の補完用途。
DO $$
BEGIN
    INSERT INTO user_group_memberships (user_id, group_id)
        SELECT up.id, '10000000-0000-0000-0000-000000000001'
        FROM user_profiles up
        WHERE up.email = 'admin_acme-corp@example.com'
          AND up.tenant_id = '00000000-0000-0000-0000-000000000002'
        ON CONFLICT (user_id, group_id) DO NOTHING;

    INSERT INTO user_group_memberships (user_id, group_id)
        SELECT up.id, '10000000-0000-0000-0000-000000000002'
        FROM user_profiles up
        WHERE up.email = 'testuser_acme-corp@example.com'
          AND up.tenant_id = '00000000-0000-0000-0000-000000000002'
        ON CONFLICT (user_id, group_id) DO NOTHING;

    INSERT INTO user_group_memberships (user_id, group_id)
        SELECT up.id, '10000000-0000-0000-0000-000000000011'
        FROM user_profiles up
        WHERE up.email = 'admin_globex-inc@example.com'
          AND up.tenant_id = '00000000-0000-0000-0000-000000000003'
        ON CONFLICT (user_id, group_id) DO NOTHING;

    INSERT INTO user_group_memberships (user_id, group_id)
        SELECT up.id, '10000000-0000-0000-0000-000000000013'
        FROM user_profiles up
        WHERE up.email = 'testuser_globex-inc@example.com'
          AND up.tenant_id = '00000000-0000-0000-0000-000000000003'
        ON CONFLICT (user_id, group_id) DO NOTHING;
END $$;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Application database initialized successfully';
    RAISE NOTICE 'Tenants: common-auth / acme-corp / globex-inc';
    RAISE NOTICE 'Tables: tenants, user_profiles, tenant_groups, user_group_memberships, permissions, group_permissions, user_permissions';
    RAISE NOTICE 'Groups: acme-corp(管理部/開発チーム/営業部), globex-inc(管理部/開発チーム/営業部)';
    RAISE NOTICE 'Row-Level Security enabled on all tables';
END $$;
