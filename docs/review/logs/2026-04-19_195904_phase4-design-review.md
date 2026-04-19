# Review Log — Phase 4 設計レビュー（FT-003/004/005）

## メタデータ
- 日時: 2026-04-19 19:59:04
- 対象: `docs/design/logs/design-003-audit-log-password-policy-session.md`
- レビュアー: Review Board（5人合議制）
- ラウンド: /review --design

## レビュー対象

差分サマリー:
- Phase 4 の設計会議記録を新規追加
- FT-003（監査ログ）、FT-004（パスワードポリシー設定）、FT-005（セッション設定）の API/DB/実装方針を定義

変更ファイル:
- docs/design/logs/design-003-audit-log-password-policy-session.md

## Phase 1 — 初見ラウンド

- PM: 3機能を同時に設計し、実装タスクまで分解できている点は良い。だが、super_admin の運用シナリオ（任意テナント管理）に対する仕様が不足している。
- Arch: API一覧にテナント解決戦略が明記されていない。特に `GET/PUT /admin/security/password-policy` と `GET/PUT /admin/security/session` が super_admin 時に対象テナント不明になる。
- Eng: `AuditService.log()` を `asyncio.create_task` のみにすると、プロセス終了時・例外時にログ欠落しうる。監査要件として信頼性の扱いを明文化すべき。
- Sec: 監査ログは「失敗しても本体継続」の方針だけでは証跡欠損リスクが高い。少なくとも失敗可視化（メトリクス/アラート）と再送戦略が必要。
- DB: `audit_logs.resource_id VARCHAR(255)` は UUID主体設計に対して曖昧。検索性能・整合性の観点で `UUID`（必要なら nullable）+ 補助キーを検討すべき。

## Phase 2 — 議論（クロスレビュー）

- Arch → PM: 既存 `admin.py` でも super_admin は `tenant_id` 明示指定を必須化した経緯がある。今回の設計でも同一原則を適用しないと再発する。
- Sec → Eng: `create_task` 自体は有効だが、監査ログに対しては「失敗が観測不能」になる実装は避けたい。最低限、失敗時に structured error log + counter を記録すべき。
- DB → Eng: 非同期化するなら Outbox テーブルやキューも選択肢。今回はコスト優先でも、設計書に将来の耐障害拡張パスを残すべき。
- PM → 全員: 今回は設計段階なので、MVPに必要な最小要件（テナント境界の明確化、監査失敗の可視化）を MUST にして、耐障害高度化は SHOULD に落とすのが妥当。

## Phase 3 — 判定

判定: **REQUEST_CHANGES**

### [MUST FIX]
1. **super_admin の対象テナント解決仕様を明記すること**
   - FT-004/005 API に `tenant_id` query を追加（super_admin は必須、tenant_admin はトークン由来）
   - FT-003 `GET /admin/audit/logs` も同様に super_admin の `tenant_id` 指定ルールを明記
2. **監査ログ失敗時の可視化要件を設計に追加すること**
   - 失敗時 structured logging（action, tenant_id, actor_id, error）
   - 監視指標（失敗件数カウンタ）とアラート方針の最低限の記述

### [SHOULD FIX]
1. `audit_logs.resource_id` の型方針を具体化（UUID主軸か、文字列主軸か）
2. 監査ログ書き込み方式に将来拡張（Outbox/Queue）を記載
3. 監査ログ API の retention/purge 方針（例: 400日保持）を運用設計として追記

### [CONSIDER]
1. FT-003 のログイン履歴 API（将来実装）のレスポンス整形を先に設計しておく
2. パスワード有効期限 UI 文言に NIST 非推奨の根拠リンク（内部 docs）を追加

### [GOOD]
- FT-003/004/005 を1つの設計に統合し、API・DB・実装方針まで一貫している
- 既存 `SecuritySettings.tsx` 拡張を前提にしており、UI導線が明確
- アクション命名規則（ドット階層記法）が整理されていて拡張しやすい

## 修正記録（/fix実行時に追記）

### 2026-04-20 — /fix

**MUST FIX #1 対応**: 「テナント解決ルール（全エンドポイント共通）」セクションを API設計冒頭に新設。super_admin は `tenant_id` クエリ必須（未指定 HTTP 400）、tenant_admin はJWT優先、`_resolve_db_tenant()` 再利用を全エンドポイントに明記。

**MUST FIX #2 対応**: 「監査ログ書き込み失敗時の可視化要件」セクションをセキュリティ設計に追加。structured error logging、`audit_log_write_failures_total` 失敗カウンタ、アラート方針を記載。擬似コード付き。

## 再レビュー（/re-review実行時に追記）

### 2026-04-20 — /re-review

**MUST FIX 解消確認:**
- #1 super_admin テナント解決仕様 → ✅ 解消済み（テーブル形式で明記, `_resolve_db_tenant()` 適用確約）
- #2 監査ログ失敗時の可視化 → ✅ 解消済み（structured log + 失敗カウンタ + アラート方針を設計に追加）

**回帰・副作用:** なし（`_resolve_db_tenant()` は既存パターンの再利用のみ）

**SHOULD FIX 3件:** 未対応だが実装フェーズでの解決を許容範囲と判断。

**判定: ✅ APPROVE**
