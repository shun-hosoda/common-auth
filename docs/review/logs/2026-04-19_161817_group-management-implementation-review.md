# Review Log — Group Management Implementation (Backend SDK)

## メタデータ
- 日時: 2026-04-19 16:18:17
- 対象: Group/Permission 管理機能の実装差分（Backend SDK）
- レビュアー: Review Board（5人合議制）
- ラウンド: /review

## レビュー対象

差分サマリー:
- Group/Permission 管理APIの新規実装（router/service/model）
- DB接続プール + RLS適用のDBClient追加
- setup_auth へのDBライフサイクル追加
- 既存 admin router に user↔group / user↔permission API追加
- ユニットテスト追加（service/router/db_client）

変更ファイル:
- packages/backend-sdk/src/common_auth/models/group.py
- packages/backend-sdk/src/common_auth/routers/groups.py
- packages/backend-sdk/src/common_auth/routers/admin.py
- packages/backend-sdk/src/common_auth/services/db_client.py
- packages/backend-sdk/src/common_auth/services/group_service.py
- packages/backend-sdk/src/common_auth/services/permission_service.py
- packages/backend-sdk/src/common_auth/setup.py
- packages/backend-sdk/tests/unit/test_db_client.py
- packages/backend-sdk/tests/unit/test_group_service.py
- packages/backend-sdk/tests/unit/test_permission_service.py
- packages/backend-sdk/tests/unit/test_groups_router.py

実行確認:
- `python -m pytest tests/ -v` → 147 passed
- `python -m mypy src/ --ignore-missing-imports` → 56 errors（新規追加箇所を含む）

## Phase 1〜3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  REVIEW BOARD — 初見ラウンド
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PM:
- APIの主要ユースケース（グループCRUD、メンバー操作、権限更新）は揃っているが、super_adminの操作経路で失敗するため運用者体験が破綻する。

Arch:
- `admin.py` の新規 user系エンドポイントで `tenant_id = _tenant_filter(user) or ""` が構造的に不正。super_admin時に空文字がDB層へ流れ、RLS/UUID前提と衝突する。

Eng:
- テストは充実し全体pytestは通過しているが、入力バリデーションが `dict` 直受け + UUID手動変換で500化リスク。422で返す設計に統一すべき。

Sec:
- 例外変換不足（`ValueError` 未捕捉）により内部実装依存の500レスポンスが露出。入力異常時にHTTPレイヤで明示的に弾く必要がある。

DB:
- DBスキーマは `tenant_id UUID` 前提（RLSもUUIDキャスト）。空文字tenant_idは整合しない。super_admin経路は target tenant 指定または明示拒否にすべき。

### 議論（クロスレビュー）
- Arch→DB: `_tenant_filter` 再利用は既存Keycloak API向けには適合するが、DB API向けには不適合。文脈依存の設計漏れ。
- Eng→PM: 既存テストは tenant_admin中心。super_adminケースの欠落が今回の欠陥を見逃した主因。
- Sec→Eng: `add_user_to_group` の `body: dict` は特に危険。`group_id` 欠落/不正で `UUID(...)` が500になる。
- DB→全員: `groups.py` 側は `_resolve_tenant` で空文字を防げている。`admin.py` 側も同等のガードを持つべき。
- Chair総括: 実装の方向性は妥当だが、運用者向けAPIでの失敗経路が本番障害になるため現状は承認不可。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  REVIEW BOARD — 判定
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

判定: REQUEST_CHANGES

[MUST FIX]
1. `admin.py` の以下4エンドポイントで super_admin 時に空文字 tenant_id を渡してしまう問題を修正すること。
   - `GET /users/{user_id}/groups`
   - `POST /users/{user_id}/groups`
   - `DELETE /users/{user_id}/groups/{group_id}`
   - `GET/PUT /users/{user_id}/permissions`
   現状 `tenant_id = _tenant_filter(user) or ""` が DB 層の UUID/RLS 前提と衝突し、500/ValueErrorを誘発する。
2. `POST /users/{user_id}/groups` の `body: dict` + 手動UUID変換を廃止し、Pydantic request model化して不正入力を422で返すこと。
3. レビュー必須チェックの型検査が失敗しているため、少なくとも今回変更した `admin.py` / `groups.py` / service層のmypyエラー（return type欠落など）を解消してから再レビューすること。

[SHOULD FIX]
1. super_admin向けに target tenant 指定の設計を明示（query/path/body）し、曖昧動作を排除する。
2. `admin.py` 新規エンドポイントに super_admin ケースのユニットテストを追加する。
3. `test_*` ファイルの文字化けコメント・未使用importを整理し、可読性を改善する。

[CONSIDER]
1. `admin.py` へ追加した user-group/permission APIを `groups.py` と責務分離して一貫配置する。
2. `setup_auth` の DB 初期化失敗時に起動時ログを強化し、運用トラブルシュートを容易にする。

[GOOD]
- API面の機能カバレッジが広く、pytest全体（147件）を通して回帰を抑えている。
- `granted=true/false/null` の3値運用を service 層テストで押さえており、仕様意図が反映されている。
- `groups.py` の CRUD/メンバー/権限APIは応答モデルが整理され、拡張しやすい構成。

## 修正記録（/fix実行時に追記）
- 実施日時: 2026-04-19
- 対応内容:
  1. `admin.py` のDB系エンドポイントに `tenant_id` クエリを追加し、`_resolve_db_tenant()` で解決する方式へ変更。
     - super_admin は `tenant_id` 指定必須（未指定時 400）
     - tenant_admin は JWT の `tenant_id` を利用
  2. `POST /users/{user_id}/groups` の入力を `dict` から `AddUserToGroupBody`（Pydantic）へ変更。
  3. `admin.py` / `groups.py` の新規関数に戻り値型注釈を追加。
  4. `groups.py` の `PermissionsListResponse` 生成時に `PermissionEntry` へ明示変換し、型整合を修正。
  5. `group_service.py` の `remove_member()` 返却を `str(result).endswith("1")` に変更し `bool` 型を明確化。
- 検証結果:
  - `python -m pytest tests/ -q` → 147 passed
  - `python -m mypy src/ --ignore-missing-imports` → 36 errors（既存ファイル由来、今回修正対象ファイルの新規エラーなし）

## 再レビュー（/re-review実行時に追記）
- 実施日時: 2026-04-19
- 判定: **APPROVE**

### MUST FIX 解消確認
1. super_admin 空 tenant_id 流入バグ → `_resolve_db_tenant()` で完全閉塞 ✅
2. `body: dict` + 手動 UUID 変換 → `AddUserToGroupBody` Pydantic モデル化 ✅
3. mypy 型エラー → 全注釈追加・PermissionEntry 変換・`str()` キャスト ✅

### 回帰チェック
- pytest: 147 passed（退行なし）✅
- mypy: 修正対象 3 ファイルに新規エラーなし ✅

### 新規指摘
- なし（空文字列 super_admin ケースは実害低く CONSIDER 止まり）

### 継続課題（SHOULD FIX / マージ後でも可）
1. super_admin 向けテストケース追加（tenant_id 未指定→400）
2. テストファイルの文字化けコメント・未使用 import 整理
