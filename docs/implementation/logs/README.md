# Implementation Logs

実装計画会議（/implement）の記録を保存するディレクトリです。

## ファイル命名規則

```
YYYY-MM-DD_HHmmss_<feature>.md
```

### 例
- `2026-02-28_110000_user-authentication.md`
- `2026-03-01_153000_payment-system.md`

## ログファイルの構造

```markdown
# 実装計画 — <機能名>

## 参加者
Architect, Senior Engineer, Security Specialist, DB Specialist, PM
+ ドメインペルソナ: （設定されている場合）

## 実装スコープ

### 新規作成ファイル
- src/...

### 修正ファイル
- src/...

## 実装方針

### アーキテクチャ
（3層アーキテクチャ、依存性注入等）

### コーディング規約
（関数サイズ、エラーハンドリング、命名規則等）

### テスト戦略
（TDD、テストレベル、カバレッジ目標）

## 実装順序

1. ...
2. ...

## TDD実装計画

（Red-Green-Refactorのサイクル）

## 議論のポイント
- 論点1: ...
- 論点2: ...

## 次のアクション
- [ ] 実装開始（TDDで進める）
- [ ] 各コンポーネント完成時に /review
- [ ] 全体完成後に統合レビュー
```
