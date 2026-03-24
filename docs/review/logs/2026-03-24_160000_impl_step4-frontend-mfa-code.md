# レビューログ — Step 4: Frontend MFA管理UI（実装レビュー）

**日時**: 2026-03-24
**ゲート**: Gate 2（実装完了）
**フェーズ**: impl
**対象**: 6ファイル差分（Modified 4 + New 2）

---

## 対象ファイル

| 状態 | ファイル |
|------|----------|
| Modified | `examples/react-app/src/api/adminApi.ts` |
| Modified | `examples/react-app/src/App.tsx` |
| Modified | `examples/react-app/src/pages/Dashboard.tsx` |
| Modified | `examples/react-app/src/pages/AdminUsers.tsx` |
| New | `examples/react-app/src/pages/SecuritySettings.tsx` |
| New | `examples/react-app/src/components/MfaStatusCard.tsx` |

---

## 指摘一覧

| ID | 重要度 | 指摘者 | 内容 | ファイル | ステータス |
|----|--------|--------|------|----------|-----------|
| M1 | MUST FIX | Eng+Arch+Sec | `fetchSettings` の useEffect 依存配列 `[fetchSettings]` → `[]` に変更。サイレントリフレッシュ時に `user` が更新 → `getAccessToken` 参照変更 → `fetchSettings` 再生成 → useEffect再発火で無限ループリスク。AdminUsers の `useEffect(() => { fetchUsers() }, [])` パターンと統一。 | `SecuritySettings.tsx` L49-L66 | ✅ `useCallback` 依存配列を `[]` に変更 |
| S1 | SHOULD FIX | Arch | Dashboard の navItems テナント管理パスが `/admin/tenants` — 他ページ（AdminUsers, SecuritySettings）は `/admin/clients`。パスの不一致を修正。 | `Dashboard.tsx` L48 | ✅ `/admin/clients` に統一 |
| S2 | SHOULD FIX | Sec | 確認ダイアログに Escape キーで閉じる機能が未実装。既存の UserDropdown は Escape 対応済み。アクセシビリティ統一のため追加を推奨。 | `SecuritySettings.tsx` L338 | ✅ `onKeyDown` で Escape 処理追加 |
| C1 | CONSIDER | Eng | MfaStatusCard の useEffect 依存配列も `[]` が望ましい。cancelled フラグで収束するため緊急度低だが、無駄なAPI呼び出しを防止。 | `MfaStatusCard.tsx` L21 | ✅ 依存配列を `[]` に変更 |

---

## 判定

| 専門家 | 判定 |
|--------|------|
| PM（佐藤） | Conditional APPROVE — M1修正必須 |
| Architect（田中） | Conditional APPROVE — M1+S1修正を推奨 |
| Senior Engineer（鈴木） | Conditional APPROVE — M1必須、S2推奨 |
| Security（高橋） | Conditional APPROVE — M1+S2修正を推奨 |
| DB/Infra（山田） | APPROVE — 指摘なし |

### 結論: Conditional APPROVE — M1（MUST FIX）修正後に /re-review を実施

---

## 良い点

- 設計書（tenant-policy.md §3）と実装の整合性が高い
- `baseOverride` パターンでエラーハンドリング統一
- 確認ダイアログが enable/disable 両方で実装済み（レビュー指摘反映済み）
- MfaStatusCard の3状態表示が明確
- TypeScript型安全性が確保されている

---

## /re-review (2026-03-24)

### 指摘解消確認

| ID | ステータス | 確認内容 |
|----|-----------|----------|
| M1 | ✅ 解消 | `useCallback(..., [])` に変更。mount時1回のみfetch。eslint-disableコメント付き。AdminUsersパターンと統一。 |
| S1 | ✅ 解消 | Dashboard navItems `/admin/tenants` → `/admin/clients`。3ページ統一。 |
| S2 | ✅ 解消 | backdrop div に `onKeyDown` Escape ハンドラ追加。 |
| C1 | ✅ 解消 | MfaStatusCard useEffect 依存配列を `[]` に変更。eslint-disableコメント付き。 |

### 回帰・副作用確認

- TypeScript型チェック: `tsc --noEmit` パス ✅
- 依存変更なし: import/export/型定義の変更なし ✅
- 機能影響なし: fetchが1回のみになるだけで操作フローに変更なし ✅
- navItemsパス統一: App.tsx のルート定義 `/admin/clients` と一致 ✅

### 別観点チェック

- Escape キーの `onKeyDown` は backdrop div に付与。div はデフォルトでフォーカスを受けないため、厳密には document level リスナーが望ましいが、実用上ボタン操作中のEscapeで機能する。将来改善の余地あり（ブロッカーではない）。

### /re-review 判定

| 専門家 | 判定 |
|--------|------|
| PM（佐藤） | APPROVE |
| Architect（田中） | APPROVE |
| Senior Engineer（鈴木） | APPROVE |
| Security（高橋） | APPROVE |
| DB/Infra（山田） | APPROVE |

### 結論: 全員一致 APPROVE ✅
