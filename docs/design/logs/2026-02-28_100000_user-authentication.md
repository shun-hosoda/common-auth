# 設計会議記録 — ユーザー認証機能

## 参加者
PM, Architect, DB Specialist, Security Specialist, Senior Engineer

## 要件サマリー

**PRD FR-003**: ユーザー認証機能
- ユーザーは登録・ログインができる
- パスワードは安全に保護される
- ログイン状態は24時間維持される

## Phase 1: 要件の理解

**PM**: 「今回実装するのは基本的な認証機能。受入基準は、新規ユーザーが登録してログインでき、24時間セッションが維持されること。MVP範囲なので、パスワードリセット等は含まない」

**Arch**: 「既存システムとの連携はなし。ただし将来的にAPI Gatewayを導入する可能性があるため、認証方式はステートレスなものが望ましい」

**DB**: 「データとして扱うエンティティは`users`のみ。email、password_hash、作成日時、更新日時を保持する」

**Sec**: 「守るべきデータはパスワードと個人情報。脅威モデルとしては、ブルートフォース攻撃、列挙攻撃、セッションハイジャックを考慮すべき」

**Eng**: 「実装の複雑度は中程度。JWT認証であれば標準ライブラリで対応可能。工数は3-4日程度」

## Phase 2: 設計提案と議論

**Arch**: 「APIエンドポイントは以下の構成を提案」
```
POST /api/auth/register — 新規登録
POST /api/auth/login    — ログイン
GET  /api/users/me      — 自分の情報取得
```

**DB**: 「Archの提案に対して、usersテーブルのスキーマは以下」
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

**Sec**: 「/api/users/meはIDOR脆弱性のリスクがない。ただし、JWTの有効期限を24時間とするなら、リフレッシュトークンの仕組みも検討すべきでは？」

**PM**: 「リフレッシュトークンはフェーズ2。MVPでは24時間で再ログインしてもらう。UX的には許容範囲」

**Eng**: 「Secの指摘を踏まえると、Middlewareで認証チェックを入れる。実装パターンはExpress middlewareで`req.user`にユーザー情報を格納」

**Arch**: 「Engの提案に同意。ただしMiddlewareはauth.middleware.tsとして独立させ、複数エンドポイントで再利用可能にする」

**Sec**: 「パスワードハッシュ化はbcrypt、ソルトラウンドは10。JWTの署名アルゴリズムはHS256で問題ないが、秘密鍵は環境変数で管理」

**DB**: 「emailカラムにUNIQUE制約を入れる。登録時の重複チェックはDB側で保証される」

## 設計決定

### API設計

```yaml
POST /api/auth/register
  Request:
    - email: string (valid email format)
    - password: string (min 8 chars)
  Response:
    - 201: { user: { id, email, created_at } }
    - 400: { error: "Invalid input" }
    - 409: { error: "Email already exists" }

POST /api/auth/login
  Request:
    - email: string
    - password: string
  Response:
    - 200: { token: string, user: { id, email } }
    - 401: { error: "Authentication failed" }

GET /api/users/me
  Headers:
    - Authorization: Bearer <token>
  Response:
    - 200: { user: { id, email, created_at } }
    - 401: { error: "Unauthorized" }
```

### DB設計

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

### セキュリティ設計

- **パスワードハッシュ**: bcrypt（ソルトラウンド10）
- **認証方式**: JWT（HS256）
- **トークン有効期限**: 24時間
- **秘密鍵管理**: 環境変数 `JWT_SECRET`
- **エラーメッセージ**: 列挙攻撃を防ぐため、ログイン失敗時は「認証に失敗しました」に統一

### 実装方針

- **アーキテクチャ**: 3層（Controller → Service → Repository）
- **認証Middleware**: `auth.middleware.ts` で実装、複数エンドポイントで再利用
- **バリデーション**: Service層入口で実施
- **エラーハンドリング**: Controller層で一括catch

## 議論のポイント

### 論点1: /api/users/me vs /api/users/{id}

- **Sec提案**: IDORを避けるため`/me`エンドポイント
- **Arch懸念**: 将来管理者が他ユーザーを見る場合の拡張性
- **PM決定**: MVP範囲では`/me`のみ。管理者機能はフェーズ2

### 論点2: リフレッシュトークン

- **Sec提案**: 24時間は長い。リフレッシュトークンでアクセストークンを短く
- **PM判断**: MVPではシンプルに。フェーズ2で対応
- **Eng同意**: 実装コストとUXのバランスからMVPでは不要

## 起票すべきADR

- **ADR-001**: JWT認証方式の選定
  - 理由: ステートレス、スケーラブル、将来のAPI Gateway導入に対応
  - トレードオフ: トークン失効管理が難しい（ブラックリスト等が必要）
  
- **ADR-002**: bcryptによるパスワードハッシュ化
  - 理由: ソルト自動生成、適応的ハッシュ関数
  - トレードオフ: 計算コストが高い（ソルトラウンドで調整）

## 次のアクション

- [x] docs/api/openapi.yaml を更新
- [x] docs/db/schema.sql を更新
- [ ] ADR-001 を起票（JWT認証）
- [ ] ADR-002 を起票（bcrypt）
- [ ] 設計レビューを実施（/review --design）
