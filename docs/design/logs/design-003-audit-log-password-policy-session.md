# 設計会議記録 — Phase 4: 監査ログ / パスワードポリシー / セッションタイムアウト

## メタデータ
- 日時: 2026-04-19
- 対象PRD: FT-003, FT-004, FT-005
- 参加者: PM, Architect, DB Specialist, Security Specialist, Senior Engineer
- ペルソナ: 認証基盤 / IDaaS, OWASP/OIDC準拠

## 要件サマリー

| ID | 機能 | 概要 |
|----|------|------|
| FT-003 | 監査ログ | ログイン履歴・権限変更の記録・可視化 |
| FT-004 | パスワードポリシー設定 | 強度・有効期限ポリシーをセキュリティ設定画面から管理 |
| FT-005 | セッションタイムアウト設定 | アイドル・最大有効期限をセキュリティ設定画面から管理 |

## 設計決定

### API設計

#### テナント解決ルール（全エンドポイント共通）

| ロール | `tenant_id` クエリ | 解決方法 |
|--------|-------------------|----------|
| `super_admin` | **必須**（未指定時 HTTP 400） | クエリパラメータの値を使用 |
| `tenant_admin` | 省略可 | JWT クレームの `tenant_id` を使用 |

実装: `_resolve_db_tenant(user, tenant_id)` ヘルパーを再利用する（admin.py に既存）。

```
# FT-003 監査ログ
GET  /admin/audit/logs
     ?tenant_id=<str>           # super_admin 必須、tenant_admin 省略可
     &action=group.*&actor_id=uuid&from=ISO8601&to=ISO8601&page=1&per_page=50
     → { logs: AuditLog[], total: int, page: int, per_page: int }

# FT-004 パスワードポリシー
GET  /admin/security/password-policy
     ?tenant_id=<str>           # super_admin 必須、tenant_admin 省略可
     → { min_length, require_uppercase, require_digits, require_special,
         password_history, expire_days }
PUT  /admin/security/password-policy
     ?tenant_id=<str>           # super_admin 必須、tenant_admin 省略可
     body: 同上

# FT-005 セッションタイムアウト
GET  /admin/security/session
     ?tenant_id=<str>           # super_admin 必須、tenant_admin 省略可
     → { access_token_lifespan, sso_session_idle_timeout, sso_session_max_lifespan }
PUT  /admin/security/session
     ?tenant_id=<str>           # super_admin 必須、tenant_admin 省略可
     body: 同上, バリデーション付き
```

### DB設計（FT-003のみ追加）

```sql
CREATE TABLE audit_logs (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID         NOT NULL REFERENCES tenants(id),
    actor_id      UUID         REFERENCES user_profiles(id) ON DELETE SET NULL,
    actor_email   VARCHAR(255),             -- 削除対策で非正規化保持
    action        VARCHAR(100) NOT NULL,    -- 'group.member.add' / 'security.mfa.update' etc.
    resource_type VARCHAR(50),
    resource_id   VARCHAR(255),
    details       JSONB        DEFAULT '{}',
    ip_address    INET,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_tenant_id_created ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(tenant_id, action);
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_logs
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);
```

### アクション命名規則（ドット階層記法）

| アクション | トリガー |
|-----------|---------|
| `group.member.add` | グループにメンバーを追加 |
| `group.member.remove` | グループからメンバーを削除 |
| `group.permission.update` | グループの権限を更新 |
| `user.permission.update` | ユーザーの直接権限を更新 |
| `security.mfa.update` | MFA設定を変更 |
| `security.password_policy.update` | パスワードポリシーを変更 |
| `security.session.update` | セッション設定を変更 |
| `auth.login.success` | ログイン成功（将来: Keycloak Events） |
| `auth.login.failure` | ログイン失敗（将来: Keycloak Events） |

### セキュリティ設計

- audit_logs に RLS 適用（tenant_id 分離）
- バックグラウンド書き込み（asyncio.create_task）→ 書き込み失敗でもメイン処理に影響しない
- ip_address: X-Forwarded-For ヘッダ対応で実 IP を取得
- FT-005 バリデーション: accessTokenLifespan 60〜3600秒, ssoSessionIdleTimeout 300〜86400秒

#### 監査ログ書き込み失敗時の可視化要件

書き込み失敗は「ベストエフォート」だが、**失敗は観測可能**にする。

| 要件 | 実装方針 |
|------|----------|
| 失敗ログ | `logger.error("audit_log_write_failed", extra={"action": action, "tenant_id": tenant_id, "actor_id": actor_id, "error": str(e)})` の structured logging |
| 失敗カウンタ | `audit_log_write_failures_total` カウンタを `AuditService` 内に保持（将来 Prometheus 連携可） |
| アラート方針 | 失敗率が一定を超えた場合のアラート設定は運用環境ごとに設定（設計では記録のみ、強制しない） |

```python
# AuditService.log() の擬似コード
async def _write(self, entry: AuditEntry) -> None:
    try:
        await self._db.execute(INSERT_SQL, ...)
    except Exception as e:
        self._failure_count += 1
        logger.error(
            "audit_log_write_failed",
            extra={"action": entry.action, "tenant_id": str(entry.tenant_id), "error": str(e)}
        )
```

### 実装方針

| 項目 | 方針 |
|------|------|
| FT-003 ストレージ | PostgreSQL audit_logs テーブル（業務DBに追加） |
| FT-003 ログイン履歴 | 将来フェーズで Keycloak Events API プロキシとして追加 |
| FT-003 サービス層 | `AuditService` クラスを新設。`log()` はバックグラウンドタスク |
| FT-003 フック | groups.py / admin.py の各ミューテーション後にフック |
| FT-004/005 Keycloak連携 | `KeycloakAdminClient` に `get_realm_settings()` / `update_realm_settings()` を追加 |
| Frontend FT-003 | 新規 `AuditLogs.tsx` ページ + SideNav に「監査ログ」追加 |
| Frontend FT-004/005 | 既存 `SecuritySettings.tsx` に新セクション追加 |

## 議論のポイント

1. **FT-003ストレージ選択**: Keycloak Events のみ vs PostgreSQL
   - Keycloak には権限変更イベントが記録されない → 業務DB側テーブルが必須
   - 認証イベントは今回スコープ外（将来 Keycloak Events API プロキシで対応）

2. **監査ログ書き込みの非同期化**:
   - 同期書き込みではパフォーマンス影響あり → asyncio.create_task で失敗許容

3. **パスワード有効期限の扱い**:
   - NIST SP 800-63B では定期変更ポリシーを非推奨
   - 設定可能にするが「NIST非推奨」の注記を UI に表示

## 起票すべきADR

- ADR-012: 監査ログストレージ戦略（PostgreSQL採用、Keycloakイベントは将来拡張）

## 次のアクション

- [ ] `docs/db/schema.sql` に audit_logs テーブル定義を追加
- [ ] `packages/backend-sdk/src/common_auth/services/audit_service.py` を新設
- [ ] `packages/backend-sdk/src/common_auth/routers/audit.py` を新設（GET /admin/audit/logs）
- [ ] `KeycloakAdminClient` に password-policy, session 設定メソッドを追加
- [ ] `admin.py` に GET/PUT /security/password-policy, /security/session を追加
- [ ] `examples/react-app/src/pages/AuditLogs.tsx` を新設
- [ ] `SecuritySettings.tsx` に PasswordPolicySection / SessionSection を追加
- [ ] ADR-012 を起票
- [ ] `/implement` で実装計画会議を実施
