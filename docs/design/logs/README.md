# Design Logs

設計会議（/design）の記録を保存するディレクトリです。

## ファイル命名規則

```
YYYY-MM-DD_HHmmss_<feature>.md
```

### 例
- `2026-02-28_100000_user-authentication.md`
- `2026-03-01_143000_payment-system.md`

## ログファイルの構造

```markdown
# 設計会議記録 — <機能名>

## 参加者
PM, Architect, DB Specialist, Security Specialist, Senior Engineer
+ ドメインペルソナ: （設定されている場合）

## 要件サマリー
（PRDからの抜粋）

## 設計決定

### API設計
（エンドポイント一覧）

### DB設計
（テーブル定義）

### セキュリティ設計
（認証・認可方式）

### 実装方針
（アーキテクチャパターン、使用技術）

## 議論のポイント
- 論点1: ...（誰がどう主張し、どう決着したか）
- 論点2: ...

## 起票すべきADR
- ADR-XXX: タイトル（簡単な説明）

## 次のアクション
- [ ] docs/api/openapi.yaml を更新
- [ ] docs/db/schema.sql を更新
- [ ] ADR-XXX を起票
- [ ] 設計レビューを実施（/review --design）
```
