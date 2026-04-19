# Review Log — グループ管理・権限設定 設計ログレビュー

## メタデータ
- 日時: 2026-04-19 00:15:00
- 対象: `docs/design/logs/2026-04-19_000000_group-management.md`
- レビュアー: Review Board（5人合議制）
- ラウンド: 1

## レビュー対象

### 差分サマリー
- 新規ファイル追加: 1件
  - `docs/design/logs/2026-04-19_000000_group-management.md`
- 変更種別: 設計会議記録（Markdown）
- コード変更: なし（`.tsx/.jsx/.ts/.py` の変更なし）

### 変更ファイル一覧
- `docs/design/logs/2026-04-19_000000_group-management.md`

---

## Phase 1: 初見ラウンド

PM:
- ユーザー要求（グループ追加、ユーザー紐付け、グループ/ユーザー別権限設定）に対して、UIとAPIの流れが漏れなく定義されている点を評価。

Arch:
- 既存方針（認証=Keycloak、認可=業務DB）とADR-003のポータビリティ方針に整合し、境界が明確。

Eng:
- 実装観点でAPI粒度とUIコンポーネント分解が適切で、既存 `/admin/users` パターン踏襲のため実装リスクが低い。

Sec:
- IDOR対策、`tenant_id` 検証、`granted=null/false` の意味分離が明記されており、誤実装リスクを下げている。

DB:
- 既存スキーマを活用しつつ、論理削除時の子グループ処理・権限解決条件（`is_active=true`）が具体化され、整合性が取れている。

---

## Phase 2: 議論（クロスレビュー）

- Sec → Eng:
  - 「`granted=null` を DELETE相当とする仕様は良いが、実装時に `false` を誤ってDELETEしないテストが必要」と指摘。
  - Eng同意。実装計画で「3値の更新テスト（true/false/null）」を必須化することで合意。

- DB → Arch:
  - 「子グループ昇格（`parent_group_id=NULL`）時に表示順の扱いをどうするか」を確認。
  - Arch回答: 初期は既存 `sort_order` を維持し、必要なら後続で再並び替え機能を追加する。

- PM → 全員:
  - MVPとして範囲を適切に絞れているか確認。
  - 全員合意: 現時点の設計はMVPとして過不足なし。

---

## Phase 3: 判定

判定: **APPROVE**

[MUST FIX]
1. なし

[SHOULD FIX]
1. 実装フェーズで `granted=true/false/null` のAPIテストケースを明示的に作成する（誤削除防止）。

[CONSIDER]
1. 将来拡張として、グループ削除後の子グループ再配置UI（ドラッグ&ドロップ）を検討。
2. 実効権限画面で「継承元グループ名」をツールチップ表示すると運用性が上がる。

[GOOD]
- 要件→API→UI→セキュリティ→実装方針まで一貫して整理されており、実装着手に必要な粒度を満たしている。
- 既存設計資産（`user-group-permission.md` / `schema_groups_permissions.sql`）を中心に据えたことで、設計の再利用性が高い。

---

## 修正記録（/fix実行時に追記）
- なし

## 再レビュー（/re-review実行時に追記）
- なし
