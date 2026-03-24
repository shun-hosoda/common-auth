# レビューログ — Step 4 実装計画: Frontend MFA管理UI

**日時**: 2026-03-24
**フェーズ**: impl（実装計画レビュー → Gate 1）
**対象**: `docs/implementation/logs/2026-03-24_100000_step4-frontend-mfa.md`
**設計書**: `docs/design/auth/mfa/tenant-policy.md` §3

---

## レビュー対象ファイル

| ファイル | 変更概要 |
|----------|---------|
| `examples/react-app/src/api/adminApi.ts` | +3型 +3関数 (MFA API) |
| `examples/react-app/src/pages/SecuritySettings.tsx` | 新規: セキュリティ設定画面 |
| `examples/react-app/src/components/MfaStatusCard.tsx` | 新規: 3状態ステータスカード |
| `examples/react-app/src/App.tsx` | +1ルート (/security) |
| `examples/react-app/src/pages/Dashboard.tsx` | navItems+1, MfaStatusCard, dropdown変更 |
| `examples/react-app/src/pages/AdminUsers.tsx` | navItems+1 |

---

## 指摘事項

### M1: MUST FIX — getMfaStatus の base URL 整合 (田中/Arch)

**問題**: `adminApi.ts` の `request` ヘルパーは `BASE = '/api/admin'` 固定。
`getMfaStatus` は `/api/auth/mfa-status` を呼ぶため、既存ヘルパーでは対応不可。
「fetch 直呼び」ではエラーハンドリングの一貫性が崩れる。

**修正**: `request` ヘルパーに `baseOverride` パラメータを追加し、
auth router (`/api/auth`) 呼び出しでもエラーハンドリングを統一する。
実装計画の合意事項 #6 に追加済み、4-1 タスク説明も更新済み。

**ステータス**: ✅ 修正済み

### S1: SHOULD FIX — MFA無効化時にも確認ダイアログ (佐藤/PM)

**問題**: 有効化(false→true)時のみ確認ダイアログが計画されているが、
無効化(true→false)もテナント全ユーザーに影響する操作であり確認が必要。

**修正**: SecuritySettings.tsx で有効化時・無効化時の両方に確認ダイアログを表示。
- 有効化: 「MFAを有効にすると、テナント内の全ユーザーに次回ログイン時からMFAが要求されます。」
- 無効化: 「MFAを無効にすると、テナント内の全ユーザーのMFA要求が解除されます。」
実装計画の合意事項 #3 を4-2 タスク説明も更新済み。検証手順に 5b（無効化確認）を追加済み。

**ステータス**: ✅ 修正済み

### C1: CONSIDER — MfaStatusCard のトークン取得方針 (鈴木/Eng)

**問題**: MfaStatusCard 内部でのトークン取得方法が不明確。

**推奨**: 内部で `useAuth().getAccessToken()` を呼ぶ（既存の AdminUsers パターンと同様）。
実装計画の合意事項 #7 と4-3 タスク説明に明記済み。

**ステータス**: ✅ 対応済み

---

## 投票結果

| 専門家 | 判定 | 条件 |
|--------|------|------|
| 佐藤(PM) | Conditional APPROVE | S1 |
| 田中(Arch) | Conditional APPROVE | M1 |
| 鈴木(Eng) | APPROVE | C1推奨 |
| 高橋(Sec) | APPROVE | — |
| 渡辺(DB) | APPROVE | — |

**最終判定**: Conditional APPROVE（M1 + S1 修正後、実装着手可）

---

## /re-review (2026-03-24)

### 指摘解消確認

| ID | ステータス | 確認内容 |
|----|----------|---------|
| M1 | ✅ 解消 | 合意事項 #6 + 4-1 タスク説明に `baseOverride` 方針明記 |
| S1 | ✅ 解消 | 合意事項 #3 に有効化・無効化両方の確認ダイアログ + 検証手順 5b 追加 |
| C1 | ✅ 解消 | 合意事項 #7 + 4-3 タスク説明に `useAuth().getAccessToken()` 明記 |

### 回帰チェック

- ファイル変更マップ: 変更なし（6ファイル構成維持）
- API仕様: 変更なし
- 実装順序・依存関係: 影響なし
- `baseOverride` はデフォルト値により既存呼び出しの後方互換性あり

### /re-review 投票

| 専門家 | 判定 |
|--------|------|
| 佐藤(PM) | APPROVE |
| 田中(Arch) | APPROVE |
| 鈴木(Eng) | APPROVE |
| 高橋(Sec) | APPROVE |
| 渡辺(DB) | APPROVE |

**最終判定**: 全員一致 APPROVE ✅
