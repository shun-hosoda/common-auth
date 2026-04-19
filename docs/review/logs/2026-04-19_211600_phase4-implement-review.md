# Review Log — Phase 4 実装レビュー（FT-003/004/005）

## メタデータ
- 日時: 2026-04-19 21:16:00
- 対象: Backend + Frontend 実装差分
- レビュアー: Review Board（5人合議）
- ラウンド: /review

## 実施チェック
- TypeScript: `examples/react-app` ✅ (`npx tsc --noEmit -p tsconfig.json`)
- TypeScript: `packages/frontend-sdk` ✅ (`npm run typecheck`)
- Backend unit tests (audit): ✅ 14 passed
- Python mypy: ❌ 既存由来のエラー 36件（今回差分外を含む）

## 判定
**REQUEST_CHANGES**

## MUST FIX
1. **監査ログ UI の action 値が backend と不一致**
   - Frontend は `group_created` 等の snake_case を前提に表示・フィルタしているが、backend は `group.create` 等の dot 記法を返す。
   - 影響: ラベル変換・フィルタが期待どおり機能しない。

2. **super_admin 時の tenant_id 指定が Frontend から渡されない**
   - `GET /admin/audit/logs` と `/security/*` は super_admin で `tenant_id` 必須仕様。
   - 現状 UI/API 呼び出しでは tenant_id を付与しておらず、super_admin で 400 を返す。

## SHOULD FIX
1. `SecuritySettings.tsx` にハードコード色（`#fee2e2` など）が散在。既存トークンへ寄せるとデザイン一貫性が高い。
2. `mypy` エラーは今回差分外が中心だが、`/push` 前の品質ゲートとしては整理が望ましい。

## 補足
- JSX/TSX の構造（return 階層、モーダル挿入、SideNav/MobileDrawer 差し替え）は前後30行で確認し、スコープ破壊はなし。
- 監査系 backend 実装（router/service/tests）はテスト観点では妥当。

## 修正記録（/fix）

### 2026-04-19 — /fix

**MUST FIX #1 対応（action 命名不一致）**
- `AuditLogs.tsx` のアクション辞書を backend の dot 記法（`group.create` / `group.member.add` / `security.password_policy.update` など）へ統一。
- バッジ色判定も dot 記法に合わせて `create/add`, `delete/remove` を判定する実装へ変更。

**MUST FIX #2 対応（super_admin tenant_id 必須）**
- `adminApi.ts` に tenant 指定対応の API を追加:
   - `listAuditLogs(..., { tenant_id })`
   - `getPasswordPolicyForTenant` / `updatePasswordPolicyForTenant`
   - `getSessionSettingsForTenant` / `updateSessionSettingsForTenant`
- `AuditLogs.tsx` / `SecuritySettings.tsx` で URL クエリ `tenant_id` を読み取り、super_admin 時は付与して呼び出すよう修正。
- super_admin かつ `tenant_id` 未指定時は、APIを叩かずに画面上で明示エラー表示。

**検証**
- `examples/react-app`: `npx tsc --noEmit -p tsconfig.json` ✅

---

## 再レビュー記録（/re-review）

### 2026-04-19 — /re-review

**検証チェック**
- TypeScript (react-app): `npx tsc --noEmit -p tsconfig.json` ✅ EXIT:0
- Backend unit tests: `pytest test_audit_service + test_audit_router` ✅ 14 passed

**MUST FIX 解消確認**
- #1 ACTION_LABELS: dot 記法11エントリに全置換済み。バッジ色判定も `includes('.delete')` / `includes('.create')` に変更済み。snake_case 残存なし。
- #2 tenant_id: `*ForTenant` API 追加・URL クエリ読み取り・super_admin guard（fetch/save/list 全ハンドラ）を実装済み。回帰なし（tenant_admin は `tenantIdFromQuery=undefined` で既存動作と同一）。

**副作用確認**
- 修正による新規型エラーなし。
- `useCallback` 依存配列に `tenantIdFromQuery` が追加されており、URL 変更時に再 fetch される。正常。
- SHOULD FIX（ハードコード色）は未対応だが判定には影響しない。

**判定: ✅ APPROVE**
