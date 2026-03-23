# Review Logs — レビューログ

このディレクトリには `/review`, `/fix`, `/re-review` のサイクルで行われたレビューの記録が保存されます。

> **⚠️ 全レビューログは永続保持。削除禁止。**

---

## ファイル命名規則

```
YYYY-MM-DD_HHmmss_<phase>_<context>.md
```

### フェーズプレフィックス（必須）

| プレフィックス | 対象工程 | レビュー内容 |
|--------------|---------|-------------|
| `req` | 要件定義 | PRD・ユーザーストーリー・MVP スコープ |
| `design` | 設計 | API仕様・DB設計・ADR・アーキテクチャ設計書 |
| `impl` | 実装 | コード差分・テスト結果・TDDサイクル |
| `test` | テスト | E2E・統合テスト・性能テスト結果 |

### 命名例

```
2026-02-28_143025_impl_user-authentication.md   — 実装レビュー
2026-03-01_163700_design_auth-module.md          — 設計レビュー
2026-03-20_120000_req_mfa-tenant-policy.md       — 要件定義レビュー
2026-03-25_100000_test_mfa-e2e.md                — テストレビュー
```

---

## ログファイルの構造

各ログファイルは以下の構造を持ちます。

```markdown
# Review Log — <タイトル>

## メタデータ
- 日時: YYYY-MM-DD HH:mm:ss
- フェーズ: 要件定義 / 設計 / 実装 / テスト
- 対象: （ブランチ名、PR番号、設計書、またはファイルパス）
- レビュアー: Review Board（5人合議制）
- ラウンド: 1 / 2 / 3

## レビュー対象

（git diff の要約、設計書一覧、またはファイル一覧）

## Phase 1: 初見ラウンド

PM: ...
Arch: ...
Eng: ...
Sec: ...
DB: ...

## Phase 2: 議論

（5人の議論の記録）

## Phase 3: 判定

判定: APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION

[MUST FIX]
1. ...

[SHOULD FIX]
1. ...

## 修正記録（/fix実行時に追記）

修正日時: YYYY-MM-DD HH:mm:ss
修正内容:
- [MUST FIX #1] ✅ ...
- [MUST FIX #2] ✅ ...

## 再レビュー記録（/re-review実行時に追記）

再レビュー日時: YYYY-MM-DD HH:mm:ss
判定: APPROVE / REQUEST_CHANGES

（解決状況と新規指摘）
```

---

## ログ一覧

| ファイル名 | フェーズ | 内容 |
|-----------|---------|------|
| `2026-02-28_143025_impl_user-authentication.md` | 実装 | Phase 1 ユーザー認証 実装レビュー |
| `2026-03-01_163700_design_auth-module.md` | 設計 | PRD・OpenAPI・DB設計一式 設計レビュー |
| `2026-03-01_213500_design_react-example-app.md` | 設計 | React Example App 設計レビュー |
| `2026-03-01_000000_impl_phase3-user-management.md` | 実装 | Phase 3 ユーザー管理 実装レビュー |
| `2026-03-20_000000_design_mfa-tenant-policy.md` | 設計 | MFAテナントポリシー 設計レビュー |
| `2026-03-20_120000_design_mfa-infrastructure.md` | 設計 | MFA基盤 設計レビュー |

---

## ログファイルの用途

1. **トレーサビリティ**: いつ誰がどのフェーズでどんな判断をしたか追跡可能
2. **学習**: 過去のレビュー指摘を参照し、同じミスを防ぐ
3. **監査**: コンプライアンス要件で品質管理プロセスの証跡が必要な場合
4. **改善**: レビューボードの判断パターンを分析し、ルール改善に活かす

## 保持ルール

- **全レビューログは永続保持する（削除禁止）**
- レビューが未完了でも記録は残す（中断理由をメタデータに追記）
- `/fix` → `/re-review` の記録は同一ファイルに追記する（ファイルを分割しない）
- `.gitignore` には追加せず、Gitで管理することを推奨
