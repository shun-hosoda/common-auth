# Review Log ? admin nav統一・グループメンバーモーダル修正・画面幅制限除去

## メタデータ
- 日時: 2026-04-20 21:51:51
- 対象: 00dab00（コミット済み）+ 未コミット4ファイル
- レビュアー: Review Board（5人合議制）
- ラウンド: Round 1

## レビュー対象

### コミット済み (00dab00)
- `auth-stack/postgres/add_audit_logs.sql` (new): audit_logsテーブル作成
- `examples/fastapi-app/main.py`: DBClient初期化追加
- `packages/backend-sdk/src/common_auth/services/db_client.py`: resolve_tenant_uuid追加
- `packages/backend-sdk/src/common_auth/services/audit_service.py`: resolve_tenant_uuid呼び出し
- `packages/backend-sdk/src/common_auth/services/group_service.py`: _rt, _to_group_dict追加
- `packages/backend-sdk/src/common_auth/services/permission_service.py`: _rt追加
- `examples/react-app/src/pages/Dashboard.tsx`: navItemsにグループ管理/監査ログ追加

### 未コミット (working tree)
- `examples/react-app/src/api/adminApi.ts`: GroupMember.added_at→joined_at, GroupMembersResponse.members→items
- `examples/react-app/src/pages/AdminGroups.tsx`: res.members→res.items, m.added_at→m.joined_at, maxWidth除去
- `examples/react-app/src/pages/AdminUsers.tsx`: navItemsにグループ管理/監査ログ追加
- `examples/react-app/src/pages/AuditLogs.tsx`: maxWidth除去

## Phase 1?3: 議論と判定

### 判定: APPROVE（SHOULD FIX は次回コミットで可）

### [MUST FIX] なし

### [SHOULD FIX]
1. `_rt` → `_resolve_tenant` リネーム（group_service.py / audit_service.py / permission_service.py）
2. add_audit_logs.sql の RLS policy に NULL動作の説明コメント追加
3. `idx_audit_logs_action` → `idx_audit_logs_tenant_action` リネーム

### [CONSIDER]
4. resolve_tenant_uuid のリクエスト単位キャッシュ検討
5. navItems 各ページハードコードを useAdminNavItems() 共有フックへ抽出

### [GOOD]
- _to_group_dict の UUID→str 変換が Pydantic v2 互換
- resolve_tenant_uuid の is_active チェックによる非アクティブテナントブロック副次効果
- adminApi.ts の型定義がバックエンド Pydantic モデルと整合
- npm run build + API疎通確認まで実施済み
