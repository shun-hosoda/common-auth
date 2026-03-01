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
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
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
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- 補足: roles カラムについて
-- Phase 1では TEXT[] で簡易実装。将来的にRBAC強化が必要な場合、
-- roles テーブル + user_roles 中間テーブルへの正規化を検討する。
