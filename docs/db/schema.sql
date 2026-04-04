-- =============================================================
-- common-auth DB Schema
-- =============================================================
-- このファイルは業務DB側のスキーマ設計の正（Single Source of Truth）です。
-- 認証データ（パスワード、MFAシークレット等）はKeycloakの内部DBに保持され、
-- ここには業務データとの紐付けに必要なテーブルのみ定義します。
--
-- 命名規約:
--   テーブル名: snake_case, 複数形 (例: users, order_items)
--   カラム名:   snake_case (例: created_at, user_id)
--   外部キー:   {参照先テーブル名の単数形}_id (例: user_id)
--   インデックス: idx_{テーブル名}_{カラム名}
-- =============================================================

-- -----------------------------------------------------------
-- テナント管理テーブル
-- Keycloak Realmと業務DBのテナント情報を紐付ける。
-- 単一テナント構成の場合は1レコードのみ。
-- -----------------------------------------------------------
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    realm_name      VARCHAR(100)  NOT NULL UNIQUE,
    display_name    VARCHAR(200)  NOT NULL,
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    settings        JSONB         DEFAULT '{}',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_realm_name ON tenants(realm_name);

-- -----------------------------------------------------------
-- ユーザープロフィールテーブル（推奨パターン）
-- Keycloakから同期されるユーザー情報を業務DB側で保持する。
-- id はKeycloakの sub クレーム（不変UUID）をそのまま使用。
-- パスワード等の認証情報はこのテーブルに保持しない。
--
-- Lazy Sync: Backend SDKのオプション機能により、
-- 初回JWT検証時に自動的にupsertされる。
-- -----------------------------------------------------------
CREATE TABLE user_profiles (
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
    -- 拡張プロフィール
    avatar_url      VARCHAR(500),
    phone_number    VARCHAR(50),
    job_title       VARCHAR(200),
    locale          VARCHAR(10)   DEFAULT 'ja',
    timezone        VARCHAR(50)   DEFAULT 'Asia/Tokyo',
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    deactivated_at  TIMESTAMPTZ,
    metadata        JSONB         DEFAULT '{}'
);

CREATE INDEX idx_user_profiles_tenant_id ON user_profiles(tenant_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);
CREATE UNIQUE INDEX idx_user_profiles_tenant_email ON user_profiles(tenant_id, email);

-- -----------------------------------------------------------
-- Row-Level Security (RLS) ポリシー
-- マルチテナントでのデータ分離を強制する（Defense in Depth）。
-- Backend SDKミドルウェアによるtenant_idフィルタリングに加え、
-- DB層でも二重にチェックを行うことでデータ漏洩リスクを最小化。
--
-- 前提条件:
--   Backend SDKで各リクエスト開始時に以下を実行:
--   SET LOCAL app.current_tenant_id = '<tenant_id>';
--
-- 単一テナント構成でRLSが不要な場合は無効化可能:
--   ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
--
-- リスク: RLS無効時、ミドルウェアのバグやORMバイパスで
--        テナント間データ漏洩が発生する可能性がある。
-- -----------------------------------------------------------
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON user_profiles
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- -----------------------------------------------------------
-- グループ・権限管理テーブル
-- テナント内の部署・チーム管理および権限制御を行う。
-- -----------------------------------------------------------

-- テナント内グループ（部署・チーム等）
CREATE TABLE tenant_groups (
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

CREATE UNIQUE INDEX uq_tg_tenant_name_active
    ON tenant_groups (tenant_id, name) WHERE is_active = TRUE;

ALTER TABLE tenant_groups ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenant_groups
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- ユーザーとグループの多対多中間テーブル
CREATE TABLE user_group_memberships (
    user_id     UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    group_id    UUID        NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    added_by    UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, group_id)
);

ALTER TABLE user_group_memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON user_group_memberships
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- 権限定義テーブル（resource × action）
CREATE TABLE permissions (
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

ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON permissions
    USING (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

-- グループへの権限割り当て
CREATE TABLE group_permissions (
    group_id       UUID        NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    permission_id  UUID        NOT NULL REFERENCES permissions(id)   ON DELETE CASCADE,
    granted        BOOLEAN     NOT NULL DEFAULT TRUE,
    granted_by     UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,
    PRIMARY KEY (group_id, permission_id)
);

ALTER TABLE group_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON group_permissions
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- ユーザーへの直接権限割り当て（グループ権限より優先）
CREATE TABLE user_permissions (
    user_id        UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    permission_id  UUID        NOT NULL REFERENCES permissions(id)   ON DELETE CASCADE,
    granted        BOOLEAN     NOT NULL DEFAULT TRUE,
    granted_by     UUID        REFERENCES user_profiles(id)          ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,
    PRIMARY KEY (user_id, permission_id)
);

ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON user_permissions
    USING (
        user_id IN (
            SELECT id FROM user_profiles
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- 実効権限ビュー（ユーザー直接権限 + グループ経由権限を統合）
CREATE OR REPLACE VIEW v_user_effective_permissions AS
SELECT
    up.user_id, p.tenant_id, p.resource, p.action, up.granted, 'direct' AS source
FROM user_permissions up
JOIN permissions p ON p.id = up.permission_id
WHERE (up.expires_at IS NULL OR up.expires_at > NOW())
UNION ALL
SELECT
    ugm.user_id, p.tenant_id, p.resource, p.action,
    BOOL_AND(gp.granted) AS granted, 'group' AS source
FROM user_group_memberships ugm
JOIN tenant_groups tg ON tg.id = ugm.group_id AND tg.is_active = TRUE
JOIN group_permissions gp ON gp.group_id = ugm.group_id
JOIN permissions p ON p.id = gp.permission_id
WHERE (gp.expires_at IS NULL OR gp.expires_at > NOW())
  AND NOT EXISTS (
    SELECT 1 FROM user_permissions up2
    WHERE up2.user_id = ugm.user_id AND up2.permission_id = gp.permission_id
      AND (up2.expires_at IS NULL OR up2.expires_at > NOW())
)
GROUP BY ugm.user_id, p.tenant_id, p.resource, p.action;

-- 補足: roles カラムについて
-- Phase 1では TEXT[] で簡易実装。将来的にRBAC強化が必要な場合、
-- roles テーブル + user_roles 中間テーブルへの正規化を検討する。
