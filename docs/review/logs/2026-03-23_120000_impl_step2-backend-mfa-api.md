# レビューログ: Step 2 — Backend API MFAテナントポリシー

**日時**: 2026-03-23
**フェーズ**: impl
**対象**: Step 2 Backend API (GET/PUT /security/mfa, GET /mfa-status, create_user MFA拡張)
**テスト結果**: 97 passed, 0 failed

## 対象ファイル

| ファイル | 変更種別 | 差分行数 |
|----------|---------|---------|
| `packages/backend-sdk/src/common_auth/routers/admin.py` | 変更 | +148 |
| `packages/backend-sdk/src/common_auth/routers/auth.py` | 変更 | +70 |
| `packages/backend-sdk/src/common_auth/services/keycloak_admin_client.py` | 変更 | +8 |
| `packages/backend-sdk/tests/unit/test_admin_router.py` | 変更 | +421 |
| `packages/backend-sdk/tests/unit/test_auth_router.py` | 新規 | +272 |
| `tests/*/__init__.py` ×3 | 新規 | pytest名前衝突解消 |

## 判定: ✅ APPROVE（条件付き）

## MUST FIX

### M2: reset_mfa の return_exceptions=True が失敗を黙殺

**場所**: admin.py L415-420 (`update_mfa_settings` 内 Step 5)
**指摘者**: Security Specialist + Senior Engineer
**問題**: `asyncio.gather(*tasks, return_exceptions=True)` で MFA reset の失敗が
完全に無視される。方式変更時に OTP クレデンシャルリセットが失敗すると認証フロー不整合。
**対応**: 失敗結果をログ記録し、`users_failed` カウントに反映する。

## SHOULD FIX

### S1: old_enabled 変数が未使用

**場所**: admin.py L399
**指摘者**: Architect
**対応**: 変数を削除する。

### S2: _MFA_SEMAPHORE のスコープコメント追記

**場所**: admin.py L335
**指摘者**: Architect + DB Specialist
**対応**: bulk メソッドを将来並列化する際にもセマフォを適用する旨をコメント記載。

### S3: テナント名をエラーメッセージから除去

**場所**: admin.py L361, L384
**指摘者**: Security Specialist
**対応**: `f"Tenant group '{user.tenant_id}' not found"` → `"Tenant group not found"`

## CONSIDER

### C1: datetime import 未使用 (auth.py)

既存コードの問題。触ったファイルなので併せて除去推奨。

### C2: test_cross_tenant_forbidden のリネーム

`test_nonexistent_tenant_group_returns_404` がより正確。

## 投票結果

| 専門家 | 判定 |
|--------|------|
| Product Manager | ✅ APPROVE |
| Architect | ⚠️ APPROVE with conditions |
| Senior Engineer | ✅ APPROVE |
| Security Specialist | ⚠️ APPROVE with conditions |
| DB Specialist | ✅ APPROVE |
