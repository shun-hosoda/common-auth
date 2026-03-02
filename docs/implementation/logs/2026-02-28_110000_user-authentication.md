# 実装計画 — ユーザー認証機能

## 参加者
Architect, Senior Engineer, Security Specialist, DB Specialist, PM

## 実装スコープ

### 新規作成ファイル
- `src/controllers/auth.controller.ts` — 認証エンドポイント
- `src/services/auth.service.ts` — 認証ビジネスロジック
- `src/repositories/user.repository.ts` — usersテーブル操作
- `src/middleware/auth.middleware.ts` — JWT検証Middleware
- `src/types/auth.types.ts` — 型定義
- `migrations/001_create_users.sql` — usersテーブル作成
- `migrations/001_create_users_down.sql` — ロールバック
- `tests/unit/services/auth.service.test.ts` — Serviceのユニットテスト
- `tests/unit/middleware/auth.middleware.test.ts` — Middlewareのユニットテスト
- `tests/integration/auth.test.ts` — 認証フローのE2Eテスト

### 修正ファイル
- `src/routes/index.ts` — 認証ルート追加
- `package.json` — bcrypt, jsonwebtoken 依存追加

## Phase 1: スコープ確認

**Arch**: 「設計書に基づき、実装が必要なコンポーネントは5つ。Controller, Service, Repository, Middleware, Typesの5層。既存プロジェクトのディレクトリ構造に従う」

**Eng**: 「既存のコードベースを確認。共通のエラーハンドリングは`src/utils/error.ts`がある。レスポンス統一フォーマットは`src/utils/response.ts`を使う」

**DB**: 「マイグレーションスクリプトは`migrations/`配下。up/downの両方を作成する。既存のマイグレーション番号は最大000なので、今回は001から開始」

**Sec**: 「パスワードハッシュ化ライブラリbcrypt、JWT生成にjsonwebtokenを使う。package.jsonに追加が必要」

## Phase 2: 実装方針の議論

**Arch**: 「Controller → Service → Repositoryの3層で実装。依存性注入はコンストラクタで行う。ServiceのコンストラクタでRepositoryを受け取る」

**Eng**: 「テスト戦略は？ControllerはE2E、ServiceとMiddlewareはユニットテスト、Repositoryはモックでテストする」

**Arch**: 「同意。RepositoryはDB操作のみなので、統合テストでDBと一緒にテストするか、モックで単体テストするかは選択可能」

**Sec**: 「認証Middlewareのテストは必須。無効なトークン、期限切れトークン、改ざんされたトークンの3パターンをテストすべき」

**DB**: 「マイグレーションは慎重に。ロールバックスクリプトも同時に作成し、本番適用前にステージング環境で動作確認する」

**PM**: 「実装順序は？ログイン機能を先に作って動作確認したい」

**Eng**: 「DB → Repository → Service → Controller の順が依存関係的に自然。ただしTDDの観点では、テストから書くのでServiceから始めるのも一案」

## 実装方針

### アーキテクチャ

```
Controller (auth.controller.ts)
  ↓ 依存
Service (auth.service.ts)
  ↓ 依存
Repository (user.repository.ts)
  ↓
DB (PostgreSQL)

Middleware (auth.middleware.ts) — 横断的関心事
```

### コーディング規約

- 関数は20行以内
- エラーは必ずthrowし、Controller層でcatch
- バリデーションはService入口で実施
- 非同期処理はasync/await
- 命名規約: キャメルケース（関数・変数）、パスカルケース（クラス・型）

### テスト戦略

- **ユニットテスト**: Service, Middleware（Repositoryはモック）
- **統合テスト**: Repository（実際のDBに接続、テストDB使用）
- **E2Eテスト**: Controller（APIエンドポイント全体）
- **カバレッジ目標**: 80%以上（主要パスを網羅）

## 実装順序

1. **マイグレーション** — usersテーブル作成（up/down）
2. **型定義** — auth.types.ts（User, RegisterInput, LoginInput等）
3. **User Repository** — CRUD操作（create, findByEmail）
4. **Auth Service** — register, login, verifyToken
5. **Auth Middleware** — JWT検証、req.userに格納
6. **Auth Controller** — エンドポイント実装
7. **テスト** — unit → integration → e2e

## TDD実装計画

### 1. User Repository

```
[Red] test: ユーザー作成が成功する
[Green] implement: create(email, passwordHash) → User
[Refactor] コードの整理

[Red] test: emailでユーザーを検索できる
[Green] implement: findByEmail(email) → User | null
[Refactor] コードの整理
```

### 2. Auth Service

```
[Red] test: 既存emailでの登録が失敗する（409エラー）
[Green] implement: register() で重複チェック
[Refactor]

[Red] test: 有効な入力で登録が成功する
[Green] implement: register() の完全実装
[Refactor]

[Red] test: 間違ったパスワードでログイン失敗（401エラー）
[Green] implement: login() でパスワード検証
[Refactor]

[Red] test: 正しい認証情報でログイン成功、JWTが返る
[Green] implement: login() の完全実装
[Refactor]

[Red] test: 無効なJWTの検証が失敗する
[Green] implement: verifyToken()
[Refactor]
```

### 3. Auth Middleware

```
[Red] test: トークンなしでリクエストが401エラー
[Green] implement: Authorizationヘッダーチェック
[Refactor]

[Red] test: 無効なトークンで401エラー
[Green] implement: JWT検証ロジック
[Refactor]

[Red] test: 有効なトークンでreq.userが設定される
[Green] implement: 完全なMiddleware
[Refactor]
```

### 4. Auth Controller（E2Eテスト）

```
[Red] test: POST /auth/register — 新規登録成功
[Green] implement: registerエンドポイント
[Refactor]

[Red] test: POST /auth/login — ログイン成功
[Green] implement: loginエンドポイント
[Refactor]

[Red] test: GET /users/me — 認証済みで自分の情報取得
[Green] implement: meエンドポイント
[Refactor]
```

## 各コンポーネントの責務

### Controller
- リクエストのバリデーション（形式チェック）
- Serviceの呼び出し
- レスポンスの整形
- エラーハンドリング（catchして適切なHTTPステータスに変換）

### Service
- ビジネスロジックの実装
- Repositoryの呼び出し
- トランザクション制御
- ドメインルールの検証（重複チェック等）

### Repository
- DB操作のみ（SQL実行）
- データの永続化・取得
- ビジネスロジックは含まない

### Middleware
- JWT検証
- req.userにユーザー情報を格納
- 認証エラー時は401レスポンス

## 議論のポイント

### 論点1: Repositoryのテスト方法

- **Eng提案**: Repositoryはモックでテストし、統合テストはE2Eで担保
- **DB懸念**: モックだとSQL構文エラーを検出できない
- **Arch結論**: Repositoryは軽量なので統合テスト推奨。テストDBを使用

### 論点2: Serviceのトランザクション管理

- **DB提案**: Serviceでトランザクションを開始・コミット
- **Eng懸念**: 今回はCRUD単純なのでトランザクション不要では
- **Arch結論**: MVPではトランザクション不要。将来複数テーブル操作が発生したら導入

## 次のアクション

- [ ] 依存パッケージのインストール（bcrypt, jsonwebtoken, @types/*）
- [ ] マイグレーションスクリプト作成
- [ ] TDDで実装開始（Repository → Service → Middleware → Controller）
- [ ] 各コンポーネント完成時に `/review` 実施
- [ ] 全体完成後に統合レビュー（`/review`）
