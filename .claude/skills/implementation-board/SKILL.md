---
name: implementation-board
description: 実装フェーズで専門家が議論して実装方針を決定する。設計完了後、コーディング開始前に使用。
---

# Implementation Board — 実装計画会議

## 概要

設計が確定した後、実装に入る前に実装計画会議を開催する。
Architect、Senior Engineer、Security、DB、PMの5人+ペルソナが議論し、実装方針を決定する。

## 事前準備

1. `docs/review/persona.md` を読み、ドメインペルソナを確認する
2. `docs/api/openapi.yaml` と `docs/db/schema.sql` の設計を確認する
3. 関連する `docs/adr/` を確認する
4. 既存のコードベース構造を確認する

## 実装計画会議の進行

### Phase 1: 設計の確認と実装スコープの特定

各専門家が自分の領域から実装対象のコンポーネントを特定する。

### Phase 2: 実装方針の議論

アーキテクチャパターン、テスト戦略、実装順序を議論する。

### Phase 3: 実装計画の確定

実装順序、TDD計画、コーディング規約を確定する。

## TDD実装計画

テスト駆動開発の順序を決定する。

```
TDD実装順序:

1. Repository / Data Layer
   [Red] テスト → [Green] 実装 → [Refactor]

2. Service / Business Logic
   [Red] テスト → [Green] 実装 → [Refactor]

3. Middleware / Infrastructure
   [Red] テスト → [Green] 実装 → [Refactor]

4. Controller / API Layer（E2Eテスト）
   [Red] テスト → [Green] 実装 → [Refactor]
```

## 出力フォーマット

```markdown
# 実装計画 — <機能名>

## 参加者
Architect, Senior Engineer, Security Specialist, DB Specialist, PM
+ ドメインペルソナ: <設定されている場合>

## 実装スコープ

### 新規作成ファイル
- ...

### 修正ファイル
- ...

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
3. ...

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

## 実装計画の記録

実装計画の記録は `docs/implementation/logs/YYYY-MM-DD_HHmmss_<feature>.md` に保存する。
