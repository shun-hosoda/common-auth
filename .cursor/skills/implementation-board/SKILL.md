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

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IMPLEMENTATION BOARD — スコープ確認
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Arch: 「設計書に基づき、実装が必要なコンポーネントは...」
      - Controller層: auth.controller.ts
      - Service層: auth.service.ts
      - Repository層: user.repository.ts
      - Middleware: auth.middleware.ts

Eng:  「既存のコードベースを確認。共通のエラーハンドリングは
       utils/error.tsがあるのでそれを使う」

DB:   「マイグレーションスクリプトも必要。001_create_users.sql」

Sec:  「パスワードハッシュ化ライブラリはbcryptを使う。
       既存プロジェクトで使っているか確認」
```

### Phase 2: 実装方針の議論

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IMPLEMENTATION BOARD — 実装方針
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Arch: 「Controller → Service → Repositoryの3層で実装」
      「依存性注入はコンストラクタで行う」

Eng:  「テストはどこまで書くか？ControllerはE2E、Serviceは
       ユニットテストで良いか」

Arch: 「同意。Repositoryもモックを使ったユニットテスト」

Sec:  「認証Middlewareのテストも必須。無効なトークン、期限切れ、
       改ざんされたトークンの3パターンをテストすべき」

DB:   「マイグレーションのロールバックスクリプトも同時に作成」

PM:   「実装順序は？ログイン機能を先に作って動作確認したい」
```

### Phase 3: 実装計画の確定

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IMPLEMENTATION BOARD — 実装計画
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

実装順序:
  1. DBマイグレーション（up/down両方）
  2. User Repository（CRUD操作）
  3. Auth Service（register, login, verifyToken）
  4. Auth Middleware（トークン検証）
  5. Auth Controller（エンドポイント実装）
  6. テスト（unit → integration → e2e）

各コンポーネントの責務:
  - Controller: リクエスト検証、レスポンス整形
  - Service: ビジネスロジック、トランザクション制御
  - Repository: DB操作のみ
  - Middleware: 認証状態検証

コーディング規約:
  - 関数は20行以内
  - エラーは必ずthrowし、Controllerでcatch
  - バリデーションはService入口で実施
```

## TDD実装計画

テスト駆動開発の順序を決定する。

```
TDD実装順序:

1. User Repository
   [Red] ユーザー作成のテスト → [Green] 実装 → [Refactor]
   [Red] ユーザー検索のテスト → [Green] 実装 → [Refactor]

2. Auth Service
   [Red] register失敗テスト（重複email） → [Green] 実装
   [Red] register成功テスト → [Green] 実装
   [Red] login失敗テスト（間違ったパスワード） → [Green] 実装
   [Red] login成功テスト → [Green] 実装

3. Auth Middleware
   [Red] 無効なトークンのテスト → [Green] 実装
   [Red] 有効なトークンのテスト → [Green] 実装

4. Auth Controller（E2Eテスト）
   [Red] POST /register のテスト → [Green] 実装
   [Red] POST /login のテスト → [Green] 実装
```

## 出力フォーマット

```markdown
# 実装計画 — <機能名>

## 参加者
Architect, Senior Engineer, Security Specialist, DB Specialist, PM
+ ドメインペルソナ: <設定されている場合>

## 実装スコープ

### 新規作成ファイル
- src/controllers/auth.controller.ts
- src/services/auth.service.ts
- src/repositories/user.repository.ts
- src/middleware/auth.middleware.ts
- migrations/001_create_users.sql

### 修正ファイル
- src/routes/index.ts （ルート追加）

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
