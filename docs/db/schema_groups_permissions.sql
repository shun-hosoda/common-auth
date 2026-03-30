-- =============================================================
-- user_profiles 拡張 + グループ・権限管理スキーマ
-- docs/design/user-group-permission.md 参照
-- =============================================================

-- =============================================================
-- 1. user_profiles 既存テーブルへのカラム追加
-- NOTE: 既存データが存在する場合、NOT NULL カラム追加時に
--       DEFAULT 値が自動適用される（PostgreSQL 11+）。
--       is_active=TRUE でアクティブとして扱われる点に注意すること。
-- =============================================================
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS avatar_url      VARCHAR(500),
    ADD COLUMN IF NOT EXISTS phone_number    VARCHAR(50),
    ADD COLUMN IF NOT EXISTS job_title       VARCHAR(200),
    ADD COLUMN IF NOT EXISTS locale          VARCHAR(10)  DEFAULT 'ja',
    ADD COLUMN IF NOT EXISTS timezone        VARCHAR(50)  DEFAULT 'Asia/Tokyo',
    ADD COLUMN IF NOT EXISTS is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deactivated_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS metadata        JSONB        DEFAULT '{}';

COMMENT ON TABLE  user_profiles              IS 'Keycloak sub と紐付くユーザープロフィール（業務属性）';
COMMENT ON COLUMN user_profiles.id           IS 'Keycloak の sub クレーム（不変UUID）';
COMMENT ON COLUMN user_profiles.roles        IS 'Keycloakレルムロールのキャッシュ（認証認可の最終判断はJWTで行う）';
COMMENT ON COLUMN user_profiles.metadata     IS 'アプリ固有の拡張フィールド（スキーマレス）';
COMMENT ON COLUMN user_profiles.is_active    IS 'FALSE=論理削除。Keycloak側も無効化すること';

-- user_profiles の RLS ポリシーを NULLIF パターンに更新（空文字キャスト失敗防止）
DROP POLICY IF EXISTS tenant_isolation_policy ON user_profiles;
CREATE POLICY tenant_isolation_policy ON user_profiles
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- updated_at 自動更新トリガー（user_profiles 用）
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================
-- 2. tenant_groups テーブル
-- テナント内の組織単位（部署・チーム等）
-- NOTE: PostgreSQL予約語 "groups" を避けるため tenant_groups と命名
-- =============================================================
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

    -- 自グループへの親参照を禁止
    CONSTRAINT chk_tg_no_self_ref CHECK (parent_group_id IS DISTINCT FROM id)
);

COMMENT ON TABLE  tenant_groups                  IS 'テナント内グループ（部署・チーム等の組織単位）。"groups" はPostgreSQL予約語のため tenant_groups を使用';
COMMENT ON COLUMN tenant_groups.parent_group_id  IS 'NULL=ルートグループ。1段階のみの階層（例: 部署→チーム）';
COMMENT ON COLUMN tenant_groups.sort_order       IS '同一階層内での表示順（小さいほど先頭）';
COMMENT ON COLUMN tenant_groups.is_active        IS 'FALSE=論理削除。削除済みグループはメンバーシップを引き継がない';

-- 同一テナント内・アクティブなグループ名は一意（論理削除済みは除外）
CREATE UNIQUE INDEX IF NOT EXISTS uq_tg_tenant_name_active
    ON tenant_groups (tenant_id, name) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_tg_tenant_id        ON tenant_groups(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tg_parent_group_id  ON tenant_groups(parent_group_id);

-- updated_at 自動更新トリガー（tenant_groups 用）
DROP TRIGGER IF EXISTS trg_tenant_groups_updated_at ON tenant_groups;
CREATE TRIGGER trg_tenant_groups_updated_at
    BEFORE UPDATE ON tenant_groups
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- RLS
-- WARNING: current_setting が空文字を返す場合に NULLIF でキャスト失敗を防ぐ
ALTER TABLE tenant_groups ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tenant_groups;
CREATE POLICY tenant_isolation ON tenant_groups
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- =============================================================
-- 3. user_group_memberships テーブル
-- ユーザーとグループの多対多中間テーブル
-- =============================================================
CREATE TABLE IF NOT EXISTS user_group_memberships (
    user_id     UUID         NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    group_id    UUID         NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    added_by    UUID         REFERENCES user_profiles(id)          ON DELETE SET NULL,
    joined_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, group_id)
);

COMMENT ON TABLE  user_group_memberships          IS 'ユーザーとグループの所属関係（多対多）';
COMMENT ON COLUMN user_group_memberships.added_by IS '追加操作を行った管理者ユーザーのID（audit用）';

CREATE INDEX IF NOT EXISTS idx_ugm_user_id   ON user_group_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_ugm_group_id  ON user_group_memberships(group_id);

-- RLS: group の tenant_id を経由してテナント分離（ビュー or アプリ制御）
ALTER TABLE user_group_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_group_memberships;
CREATE POLICY tenant_isolation ON user_group_memberships
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- =============================================================
-- 4. permissions テーブル
-- リソース×アクションの権限定義
-- =============================================================
CREATE TABLE IF NOT EXISTS permissions (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID         REFERENCES tenants(id) ON DELETE CASCADE,  -- NULL=システム共通
    resource     VARCHAR(100) NOT NULL,
    action       VARCHAR(50)  NOT NULL,
    description  TEXT,
    is_system    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- is_system=TRUE のシステム権限は tenant_id が NULL であること（スプーフィング防止）
    -- is_system=FALSE のカスタム権限は必ず tenant_id を持つこと
    CONSTRAINT chk_permissions_system_tenant
        CHECK (
            (is_system = TRUE  AND tenant_id IS NULL)
            OR
            (is_system = FALSE AND tenant_id IS NOT NULL)
        )
);

COMMENT ON TABLE  permissions            IS '権限定義（resource × action の組み合わせ）';
COMMENT ON COLUMN permissions.tenant_id  IS 'NULL=全テナント共通のシステム権限。テナント固有権限は tenant_id を設定';
COMMENT ON COLUMN permissions.is_system  IS 'TRUE=システム定義権限（削除・編集不可）。必ず tenant_id=NULL';
COMMENT ON COLUMN permissions.resource   IS '対象リソース名（例: users, reports, billing, settings）';
COMMENT ON COLUMN permissions.action     IS '操作種別（read, write, delete, admin, export）';

-- UNIQUE制約: NULLはUNIQUEで複数許可されるため部分インデックスで実現
-- システム権限（tenant_id IS NULL）の重複防止
CREATE UNIQUE INDEX IF NOT EXISTS uq_perm_system_resource_action
    ON permissions (resource, action) WHERE tenant_id IS NULL;
-- テナント固有権限（tenant_id IS NOT NULL）の重複防止
CREATE UNIQUE INDEX IF NOT EXISTS uq_perm_tenant_resource_action
    ON permissions (tenant_id, resource, action) WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_permissions_tenant_id ON permissions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_permissions_resource   ON permissions(resource);

-- RLS: システム権限（tenant_id IS NULL）は全テナントから参照可能
-- WARNING: NULLIF で空文字を NULL に変換してキャスト失敗を防ぐ
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON permissions;
CREATE POLICY tenant_isolation ON permissions
    USING (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

-- =============================================================
-- 5. group_permissions テーブル
-- グループへの権限割り当て
-- =============================================================
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id       UUID         NOT NULL REFERENCES tenant_groups(id) ON DELETE CASCADE,
    permission_id  UUID         NOT NULL REFERENCES permissions(id)   ON DELETE CASCADE,
    granted        BOOLEAN      NOT NULL DEFAULT TRUE,  -- FALSE=明示的拒否
    granted_by     UUID         REFERENCES user_profiles(id)          ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,  -- NULL=無期限。期限付き付与に利用

    PRIMARY KEY (group_id, permission_id)
);

COMMENT ON TABLE  group_permissions           IS 'グループへの権限割り当て';
COMMENT ON COLUMN group_permissions.granted   IS 'TRUE=許可, FALSE=明示的拒否（ユーザー直接権限で上書き可能）';
COMMENT ON COLUMN group_permissions.granted_by IS '設定した管理者（audit用）';
COMMENT ON COLUMN group_permissions.expires_at IS 'NULL=無期限。設定時は有効期限内のみ権限が有効';

CREATE INDEX IF NOT EXISTS idx_gp_group_id       ON group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_gp_permission_id  ON group_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_gp_expires_at     ON group_permissions(expires_at) WHERE expires_at IS NOT NULL;

-- RLS: group の tenant_id を経由
ALTER TABLE group_permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON group_permissions;
CREATE POLICY tenant_isolation ON group_permissions
    USING (
        group_id IN (
            SELECT id FROM tenant_groups
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- =============================================================
-- 6. user_permissions テーブル
-- ユーザーへの直接権限割り当て（グループ権限より優先）
-- =============================================================
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id        UUID         NOT NULL REFERENCES user_profiles(id)  ON DELETE CASCADE,
    permission_id  UUID         NOT NULL REFERENCES permissions(id)    ON DELETE CASCADE,
    granted        BOOLEAN      NOT NULL DEFAULT TRUE,  -- FALSE=明示的拒否
    granted_by     UUID         REFERENCES user_profiles(id)           ON DELETE SET NULL,
    granted_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMPTZ,  -- NULL=無期限。期限付き付与に利用

    PRIMARY KEY (user_id, permission_id)
);

COMMENT ON TABLE  user_permissions         IS 'ユーザーへの直接権限割り当て（グループ権限より優先）';
COMMENT ON COLUMN user_permissions.granted IS 'TRUE=許可, FALSE=明示的拒否（グループ権限を打ち消す）';
COMMENT ON COLUMN user_permissions.expires_at IS 'NULL=無期限。設定時は有効期限内のみ権限が有効';

CREATE INDEX IF NOT EXISTS idx_up_user_id         ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_up_permission_id   ON user_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_up_expires_at      ON user_permissions(expires_at) WHERE expires_at IS NOT NULL;

-- RLS: user_profiles の tenant_id を経由
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_permissions;
CREATE POLICY tenant_isolation ON user_permissions
    USING (
        user_id IN (
            SELECT id FROM user_profiles
             WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        )
    );

-- =============================================================
-- 7. システム共通権限プリセット（初期データ）
-- NOTE: ON CONFLICT は部分インデックス (WHERE tenant_id IS NULL) を指定
-- =============================================================
INSERT INTO permissions (tenant_id, resource, action, description, is_system) VALUES
    -- ユーザー管理
    (NULL, 'users',    'read',   'ユーザー一覧・詳細の参照',                 TRUE),
    (NULL, 'users',    'write',  'ユーザーの作成・編集',                     TRUE),
    (NULL, 'users',    'delete', 'ユーザーの削除',                           TRUE),
    (NULL, 'users',    'admin',  'MFAリセット・パスワードリセット等の管理操作', TRUE),
    -- グループ管理
    (NULL, 'groups',   'read',   'グループ一覧・詳細の参照',   TRUE),
    (NULL, 'groups',   'write',  'グループの作成・編集',        TRUE),
    (NULL, 'groups',   'admin',  'グループメンバーの管理',      TRUE),
    -- レポート
    (NULL, 'reports',  'read',   'レポートの参照',     TRUE),
    (NULL, 'reports',  'export', 'レポートのエクスポート', TRUE),
    -- 請求
    (NULL, 'billing',  'read',   '請求情報の参照',   TRUE),
    (NULL, 'billing',  'admin',  '請求設定の変更',   TRUE),
    -- テナント設定
    (NULL, 'settings', 'read',   'テナント設定の参照', TRUE),
    (NULL, 'settings', 'write',  'テナント設定の変更', TRUE)
ON CONFLICT (resource, action) WHERE tenant_id IS NULL DO NOTHING;

-- =============================================================
-- 8. 権限チェック用ビュー（アプリから参照しやすくする）
-- WARNING: このビューは SECURITY INVOKER（デフォルト）。
--   呼び出し元のロールに各テーブルへの SELECT 権限が必要。
--   アプリロール (app_user) は app.current_tenant_id を設定してから参照すること。
--   RLS が有効なため、app.current_tenant_id 未設定時は全行が返らない。
--
-- NOTE: tenant_admin の初期権限付与フロー
--   新テナント作成時にアプリ側で以下の処理を実行すること:
--   1. tenant_groups に管理者グループを INSERT
--   2. permissions からシステム権限（tenant_id IS NULL）を SELECT
--   3. 管理者グループに全権限を group_permissions で INSERT
--   4. tenant_admin ユーザーを user_group_memberships で管理者グループへ追加
-- =============================================================
CREATE OR REPLACE VIEW v_user_effective_permissions AS
-- ユーザー直接権限（最優先）
-- NOTE: PK (user_id, permission_id) で一意のため重複なし
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

-- グループ経由の権限（ユーザー直接権限が存在しないリソース×アクションのみ）
SELECT
    ugm.user_id,
    p.tenant_id,
    p.resource,
    p.action,
    -- いずれかのグループが拒否していれば拒否
    BOOL_AND(gp.granted) AS granted,
    'group'  AS source
FROM user_group_memberships ugm
JOIN tenant_groups tg ON tg.id = ugm.group_id AND tg.is_active = TRUE
JOIN group_permissions gp ON gp.group_id = ugm.group_id
JOIN permissions p ON p.id = gp.permission_id
WHERE (gp.expires_at IS NULL OR gp.expires_at > NOW())
  AND NOT EXISTS (
    -- 有効な（期限内の）直接権限が存在する場合はグループ権限をスキップ
    -- NOTE: expires_at も考慮しないと期限切れの直接権限がグループ権限を遮断する
    SELECT 1 FROM user_permissions up2
    WHERE up2.user_id = ugm.user_id
      AND up2.permission_id = gp.permission_id
      AND (up2.expires_at IS NULL OR up2.expires_at > NOW())
)
GROUP BY ugm.user_id, p.tenant_id, p.resource, p.action;

COMMENT ON VIEW v_user_effective_permissions IS
    'ユーザーの実効権限ビュー。直接権限がグループ権限より優先される。'
    'expires_at を考慮して期限切れ権限を除外する。'
    'RLS に依存するため app.current_tenant_id の設定が必須。';
