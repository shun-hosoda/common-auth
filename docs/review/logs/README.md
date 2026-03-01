# Review Logs

このディレクトリには `/review`, `/fix`, `/re-review` のサイクルで行われたレビューの記録が保存されます。

## ファイル命名規則

```
YYYY-MM-DD_HHmmss_<context>.md
```

### 例
- `2026-02-28_143025_feature-auth.md` — ブランチ feature/auth のレビュー
- `2026-02-28_150130_PR-42.md` — PR #42のレビュー
- `2026-02-28_161500_src-api-user.md` — 特定ファイルのレビュー

## ログファイルの構造

各ログファイルは以下の構造を持ちます。

```markdown
# Review Log — <タイトル>

## メタデータ
- 日時: YYYY-MM-DD HH:mm:ss
- 対象: （ブランチ名、PR番号、またはファイルパス）
- レビュアー: Review Board（5人合議制）
- ラウンド: 1 / 2 / 3

## レビュー対象

（git diff の要約、またはファイル一覧）

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

## ログファイルの用途

1. **トレーサビリティ**: いつ誰がどんな判断をしたか追跡可能
2. **学習**: 過去のレビュー指摘を参照し、同じミスを防ぐ
3. **監査**: コンプライアンス要件で品質管理プロセスの証跡が必要な場合
4. **改善**: レビューボードの判断パターンを分析し、ルール改善に活かす

## 保持期間

- 本番リリースされたコミットのログは永続保持
- マージされなかったブランチのログは適宜削除可
- `.gitignore` には追加せず、Gitで管理することを推奨
