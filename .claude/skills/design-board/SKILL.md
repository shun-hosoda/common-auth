---
name: design-board
description: 設計フェーズで専門家が議論して最適な設計を決定する。PRD確定後、API/DB設計時に使用。
---

# Design Board — 設計会議

## 概要

要件が確定した後、実装に入る前に設計会議を開催する。
PM、Architect、DB、Security、Engineerの5人+ペルソナが議論し、設計の妥当性を検証する。

## 事前準備

1. `docs/review/persona.md` を読み、ドメインペルソナを確認する
2. `docs/prd/prd.md` の要件を確認する
3. 既存の `docs/adr/`, `docs/api/`, `docs/db/` を確認する

## 設計会議の進行

### Phase 1: 要件の理解（各専門家の視点）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DESIGN BOARD — 要件理解
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PM:   「今回実装するのは〇〇機能。受入基準は△△」
Arch: 「既存システムとの連携は□□が必要」
DB:   「データとして扱うエンティティは...」
Sec:  「守るべきデータは...、脅威モデルは...」
Eng:  「実装の複雑度と工数の観点から...」
```

### Phase 2: 設計提案と議論

各専門家が自分の領域から設計案を提示し、他の専門家と議論する。

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DESIGN BOARD — 設計提案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Arch: 「APIエンドポイントは以下の構成を提案」
      - POST /api/users
      - GET  /api/users/{id}

DB:   「Archの提案に対して、usersテーブルのスキーマは...」
      「外部キーとして...が必要」

Sec:  「認証は/api/users/{id}でIDOR脆弱性のリスクがある。
       現在のユーザーIDとパスの{id}を検証する必要がある」

Eng:  「Secの指摘を踏まえると、Middlewareで認可チェックを入れるべき。
       実装パターンとしては...」

Arch: 「Engの提案に同意。ただし将来的に管理者が他ユーザーを見る
       ケースを考慮し、権限レベルの概念を入れたい」

PM:   「管理者機能はフェーズ2。MVPではシンプルに自分の情報のみ
       アクセス可能にする方が良い」
```

### Phase 3: 設計決定とADR起票

議論を踏まえ、設計を確定する。重要な判断はADRに記録する。

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DESIGN BOARD — 決定事項
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[API設計]
- POST /api/auth/register
- POST /api/auth/login
- GET  /api/users/me （自分の情報のみ）

[DB設計]
- usersテーブル: id, email, password_hash, created_at, updated_at
- 外部キー: なし（MVPフェーズ）

[セキュリティ]
- JWT認証
- Middlewareでトークン検証
- /users/meエンドポイントで自己情報のみアクセス

[ADR起票]
- ADR-001: JWT認証方式の選定
  理由: ステートレス、スケーラブル、フロントエンドとの親和性
```

## 出力フォーマット

設計会議の結果を以下の形式で出力する：

```markdown
# 設計会議記録 — <機能名>

## 参加者
PM, Architect, DB Specialist, Security Specialist, Senior Engineer
+ ドメインペルソナ: <設定されている場合>

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

## 設計会議の記録

設計会議の記録は `docs/design/logs/YYYY-MM-DD_HHmmss_<feature>.md` に保存する。
