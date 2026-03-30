# レビューログ: テストグループ・シードデータ追加

**日時:** 2026-03-30  
**フェーズ:** impl（実装）  
**対象差分:** テストテナント追加・テストグループ・権限・自動割り当てトリガー追加

## 対象ファイル

- `auth-stack/postgres/init.sql` (+141行)
- `auth-stack/README.md` (+25行)

---

## レビュー結果

| 重要度 | 件数 | 状態 |
|--------|------|------|
| 🔴 MUST FIX | 2件 | ✅ 修正済み |
| 🟡 SHOULD FIX | 2件 | 1件修正済み / 1件次回課題 |
| 💡 INFO | 1件 | 記録のみ |

---

## 🔴 MUST（全件修正済み）

### M1: `ON CONFLICT DO NOTHING` ターゲット未指定 → 修正済み

**指摘者:** シニアエンジニア / DB専門家  
**内容:** `tenant_groups`, `group_permissions`, `user_group_memberships` の全 INSERT で
`ON CONFLICT DO NOTHING` が使われており、どの制約に対して無視するかが不明確だった。
複数の UNIQUE 制約（特に部分インデックス）が存在するテーブルでは保守性・デバッグ容易性が低下する。

**修正内容:**

```sql
-- Before
ON CONFLICT DO NOTHING;

-- After (tenant_groups)
ON CONFLICT (id) DO NOTHING;

-- After (group_permissions)
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- After (user_group_memberships)
ON CONFLICT (user_id, group_id) DO NOTHING;
```

### M2: `fn_auto_assign_test_groups` に本番混入防止の警告コメント未記載 → 修正済み

**指摘者:** セキュリティ専門家  
**内容:** email プレフィックスでグループを決定するロジックは本番アンチパターン。
`CREATE OR REPLACE` で定義されるため、将来的に本番DBへ誤適用されるリスクがあった。

**修正内容:**

```sql
-- ⚠️  WARNING: TEST-ONLY FUNCTION. DO NOT APPLY TO PRODUCTION.
--              email プレフィックスでグループ割り当てを決定するのは
--              本番環境におけるアンチパターンです。
--              本番DBへのマイグレーション時はこの関数を含めないこと。
```

---

## 🟡 SHOULD（1件修正済み、1件次回）

### S1: フォールバック DO $$ ブロックのコメント補足 → 修正済み

`docker-compose down -v` 後の初回起動時に `user_profiles` が空のため INSERT が 0行になる旨を
コメントに明記。誤解防止と運用ガイダンスの向上。

### S2: `v_user_effective_permissions` ビューの `security_barrier` 未設定 → **次回課題**

**内容:** ビューにセキュリティバリアが付与されていない。PostgreSQL がビュー越しに
RLS 回避の最適化を行う可能性がある（理論的リスク）。

**対応:** 今回の差分外のため次回実装時に対応。

```sql
-- 推奨形式
CREATE OR REPLACE VIEW v_user_effective_permissions
WITH (security_barrier = true) AS ...
```

---

## 💡 INFO

### I1: init.sql での RLS と superuser 実行の関係

Docker 初期化スクリプトは superuser（`app_user` に CREATEDB 権限あり or postgres ユーザー）で
実行されるため、RLS は `BYPASSRLS` 設定により影響を受けない。
`permissions` テーブルへの INSERT（`tenant_id IS NULL` のシステム権限）は RLS ポリシーの
`tenant_id IS NULL` 分岐でも許可されるため、実際は問題なし。

---

## 承認状態

- **APPROVE（修正条件付き）** → MUST 2件の修正完了により **APPROVE**

---

## 次回レビュー時の確認事項

1. `v_user_effective_permissions` への `security_barrier = true` 付与
2. フロントエンド（管理画面）からのグループ一覧・メンバー表示の動作確認
