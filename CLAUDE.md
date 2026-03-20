# CLAUDE.md — AI Autonomous Development Environment

このファイルはAIエージェントがプロジェクトを理解するためのエントリーポイントです。

## ⚠️ 工程分離ルール（最重要）

**各工程は必ず独立して実行すること。工程をまたいで自動的に次の工程へ進んではならない。**

| 工程 | 担当モデル（推奨） | 完了条件 | 次工程への移行 |
|------|-----------------|---------|--------------|
| 要件定義 | o3 / o1 | PRD承認 | **ユーザーが明示的に「設計へ」と指示** |
| 設計 | o3 / Claude Opus | 設計書・ADR承認 | **ユーザーが明示的に「実装へ」と指示** |
| 実装・テスト | Claude Sonnet / GPT-4.1 | レビューAPPROVE | **ユーザーが明示的に「pushへ」と指示** |

### 停止ルール

- 要件定義完了後 → **「✅ 要件定義完了。設計工程に進む場合は『/design』を実行してください。」と出力して停止**
- 設計完了後 → **「✅ 設計完了。実装工程に進む場合は『/implement』を実行してください。」と出力して停止**
- 実装完了後 → **「✅ 実装完了。レビューを行う場合は『/review』を実行してください。」と出力して停止**
- レビューAPPROVE後 → **「✅ レビュー承認済み。プッシュする場合は『/push』を実行してください。」と出力して停止**

### /push 実行フロー

```
1. git status で .env 等のシークレットが混入していないことを確認する
2. 対象ファイルを git add する
3. git commit -m "<コミットメッセージ>" を実行する
4. git push origin <ブランチ> を実行する
5. 完了後「✅ Push完了」を出力して終了する
```

> ユーザーの許可確認は不要。/push コマンドの受信をもって実行許可とみなす。
> .env 等のシークレットファイルが検出された場合のみ中断し、警告を出力する。

> AIは各工程の成果物を出力した後、**次工程を自律的に開始してはならない。**

---

## プロジェクト構造

```
.
├── .cursor/
│   ├── rules/                # AIの行動ルール
│   │   ├── core_rules.mdc        # 基本原則（設計ゲート・品質基準）【最優先】
│   │   ├── autonomous_workflow.mdc # 実装前ゲートチェック・タスク分類【最優先】
│   │   ├── self_optimization.mdc # 自己最適化・コンテキスト効率化【常時】
│   │   ├── efficient_workflow.mdc # 階層化レビュー・バッチ処理
│   │   ├── commands.mdc          # スラッシュコマンド定義
│   │   ├── review_process.mdc    # レビューサイクル制御
│   │   ├── tdd.mdc              # テスト駆動開発
│   │   └── git_conventions.mdc  # Git規約
│   └── skills/               # AI専門家ペルソナ
│       ├── design-board/         # 設計会議（5人議論）
│       ├── implementation-board/ # 実装計画会議（5人議論）
│       ├── review-board/         # レビュー会議（5人議論）
│       ├── product-manager/      # PM: 要件・MVP検証
│       ├── architect/            # 構造・疎結合・拡張性
│       ├── senior-engineer/      # コード品質・保守性
│       ├── security-specialist/  # OWASP・脆弱性
│       ├── db-specialist/        # スキーマ・クエリ最適化
│       └── ui-design/            # UIデザイン設計・実装（汎用SaaS UI）
├── docs/
│   ├── prd/                  # プロダクト要件定義書
│   ├── adr/                  # アーキテクチャ決定記録
│   ├── api/                  # API仕様（OpenAPI）
│   ├── db/                   # DB設計
│   ├── design/               # 設計会議記録
│   │   └── logs/                 # /design の記録
│   ├── implementation/       # 実装計画記録
│   │   └── logs/                 # /implement の記録
│   └── review/               # レビュー設定・記録
│       ├── persona.md            # ドメインペルソナ設定
│       ├── strategy.md           # レビュー戦略
│       ├── checklist.md          # チェックリスト
│       └── logs/                 # /review の記録
├── src/                      # アプリケーションコード
├── tests/                    # テストコード（unit/integration/e2e）
├── infra/                    # IaC（Terraform, Docker等）
└── .github/workflows/        # CI/CDパイプライン
```

## コマンド体系

### 効率モード（トークン節約）⚡

| コマンド | トークン | 用途 |
|----------|---------|------|
| `/quick` | 20% | 小さな修正、バグ修正、50行以下の変更 |
| `/batch 1-3` | 40% | 複数Stepをまとめて実装、1回だけレビュー |
| `/cycle` | 60% | 標準の実装・テスト・レビューサイクル |

### 詳細モード（従来通り）

| コマンド | 動作 |
|----------|------|
| `/design` | 5人専門家による設計会議（API/DB/セキュリティ設計） |
| `/implement` | 5人専門家による実装計画会議（TDD計画、実装順序） |
| `/review` | 5人専門家レビューボード会議を開催 |
| `/fix` | レビュー指摘（MUST/SHOULD FIX）を修正 |
| `/re-review` | 修正後の再レビュー（指摘解消確認 + 変更起因の別観点レビュー） |

### Git操作

| コマンド | 動作 |
|----------|------|
| `/push` | 承認済み成果物を即座に `git add` → `git commit` → `git push` する（許可確認不要） |
| `/test` | 単体テスト実行・分析 |

## ⛔ 実装前ゲートチェック（必須）

タスクを受けたら **最初に分類を宣言する**:

| 分類 | 条件 | 実装前に必要なこと |
|------|------|----------------|
| Hotfix | ≤10行, バグ修正のみ | なし（Level 1チェックのみ） |
| Minor | ≤50行, 既存機能改善 | なし（Level 2クイックレビュー） |
| **Standard** | **新機能, 新ファイル** | **⛔ /design → /review 必須** |
| **Major** | **アーキテクチャ変更** | **⛔ /design → ADR → /review 必須** |

## 開発フロー

```
【工程1: 要件定義】← ここで停止 ✋
  ↓ ユーザー指示待ち
【工程2: 設計】/design → /implement ← ここで停止 ✋
  ↓ ユーザー指示待ち
【工程3: 実装・テスト】TDD ← ここで停止 ✋
  ↓ ユーザー指示待ち
【工程4: レビュー】/review → /fix → /re-review ← ここで停止 ✋
  ↓ ユーザー指示待ち
【工程5: リリース】/push
```

### 工程ごとの推奨モデル

```
工程1 要件定義: 思考力重視 → o3, o1, Claude Opus
工程2 設計:     思考力重視 → o3, Claude Opus
工程3 実装:     コード生成  → Claude Sonnet, GPT-4.1, Gemini 2.5 Pro
工程4 レビュー: 思考力重視 → o3, Claude Opus
工程5 Push:     軽量タスク  → Claude Haiku, GPT-4o-mini
```

### フェーズ詳細

1. **要件定義**: `docs/prd/prd.md` に要件を記入 → **停止**
2. **設計会議**: `/design` で5人専門家が議論 → API/DB設計を確定 → **停止**
3. **実装計画**: `/implement` でTDD計画と実装順序を決定 → **停止**
4. **実装**: TDDサイクル（Red → Green → Refactor） → **停止**
5. **レビュー**: `/review` で5人専門家が差分レビュー → **停止**
6. **修正**: `/fix` で指摘事項を修正 → **停止**
7. **再レビュー**: `/re-review` で修正結果を検証（指摘の解消確認 + 回帰/副作用 + セキュリティ等の別観点チェック）→ APPROVE後 **停止**
8. **プッシュ**: `/push` でコミット＆プッシュ

## トークン効率化

品質を維持しながらトークン消費を抑えるための仕組み:

### 階層化レビュー

```
Level 1: 自動チェック（リンター + テスト）→ 問題なければ完了
Level 2: 簡易レビュー（1視点でクイックチェック）
Level 3: 詳細レビュー（5人専門家、重要な変更時のみ）
```

### /re-review 運用方針

- 必須: 前回 `/review` の MUST/SHOULD 指摘の解消確認
- 必須: 修正による回帰・副作用の確認
- 推奨: 修正箇所に関連する別観点（例: セキュリティ、権限境界、運用性）を差分中心で再点検

### コンテキスト効率化

- `docs/_summary.md` — 全設計書の要約（毎回全文読み込みを回避）
- 差分ベース読み込み — 変更ファイルのみ参照
- スマート専門家選択 — 変更内容に応じて必要な専門家のみ参加

### 推奨ワークフロー

| 変更規模 | 推奨コマンド |
|---------|-------------|
| 小（<50行）| `/quick` |
| 中（複数Step）| `/batch` |
| 大（設計変更）| `/design` → `/implement` → `/cycle` |

## 初期セットアップ

1. `docs/review/persona.md` にドメインペルソナを設定する
2. `docs/prd/prd.md` にプロダクト要件を記入する
3. AIに「PRDに基づいて開発を開始してください」と指示する

## コマンド（プロジェクトに応じて設定）

```bash
# テスト: npm test / pytest / go test ./...
# リント: npm run lint / ruff check . / golangci-lint run
# ビルド: npm run build / python -m build / go build ./...
```

---

## 🔥 既知の落とし穴（AIが最初に読むこと）

このプロジェクトで過去に繰り返し発生したバグ一覧。
**症状と一致したら、診断コマンドを実行して即自己解決すること。**

---

### P1: `hasRole('tenant_admin')` が常に false を返す

**症状**: `admin_*@example.com` でログインしても管理画面に遷移できない / SideNav にユーザー管理が表示されない

**根本原因**: Keycloak の `roles` クライアントスコープの `realm roles` マッパーで `id.token.claim` が `false`（未設定）。
`oidc-client-ts` の `user.profile` は IDトークン由来なのでロールが空になる。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$sc = (Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/client-scopes' -Headers @{Authorization="Bearer $t"}) | Where-Object { $_.name -eq 'roles' }
$mp = Invoke-RestMethod -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models" -Headers @{Authorization="Bearer $t"}
$mp | ForEach-Object { "$($_.name): id.token=$($_.config.'id.token.claim')" }
# ✅ 正常: realm roles: id.token=true
# ❌ 異常: realm roles: id.token= (空)
```

**自己修正コマンド**:
```powershell
# 上記の $t, $sc, $mp を取得済みの前提
$rm = $mp | Where-Object { $_.name -eq 'realm roles' }
$rm.config | Add-Member -MemberType NoteProperty -Name 'id.token.claim' -Value 'true' -Force
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models/$($rm.id)" -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body ($rm | ConvertTo-Json -Depth 10)
$cm = $mp | Where-Object { $_.name -eq 'client roles' }
$cm.config | Add-Member -MemberType NoteProperty -Name 'id.token.claim' -Value 'true' -Force
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models/$($cm.id)" -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body ($cm | ConvertTo-Json -Depth 10)
Write-Host 'Fixed. ブラウザで再ログインしてください。'
```

**恒久対策済み**:
- `auth-stack/keycloak/realm-export.json` の `realm roles` / `client roles` マッパーに `"id.token.claim": "true"` を追加済み
- `packages/frontend-sdk/src/AuthProvider.tsx` の `extractRealmRoles()` がアクセストークンを優先して読むよう修正済み（二重防御）

---

### P2: パスワードリセットメールが届かない

**症状**: Keycloak のパスワードリセットを実行しても MailHog に何も届かない

**根本原因**: `realm-export.json` の SMTP 設定に `"#{SMTP_HOST}"` というリテラル文字列（プレースホルダー未展開）が入っていた。
`docker-compose down -v` + 再起動でこの設定が再インポートされると再発する。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$realm = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth' -Headers @{Authorization="Bearer $t"}
$realm.smtpServer | ConvertTo-Json
# ✅ 正常: "host": "mailhog", "port": "1025"
# ❌ 異常: "host": "#{SMTP_HOST}" または空
```

**自己修正コマンド**:
```powershell
$body = @{smtpServer=@{host='mailhog';port='1025';from='noreply@example.com';fromDisplayName='Common Auth';auth='false';ssl='false';starttls='false'}} | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri 'http://localhost:8080/admin/realms/common-auth' -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body $body
Write-Host 'Fixed. Keycloak再起動不要。'
```

**恒久対策済み**: `auth-stack/keycloak/realm-export.json` の `smtpServer` を `mailhog:1025` に修正済み。

---

### P3: SDK変更がブラウザに反映されない

**症状**: `packages/frontend-sdk/src/` を編集してもブラウザの動作が変わらない

**根本原因**: `npm run dev`（Vite）はローカルパッケージを自動ビルドしない。
かつ `node_modules/.vite` キャッシュが古いビルドを保持する。

**診断確認**:
```powershell
# dist が src より古い = ビルド未実施
Get-Item packages/frontend-sdk/dist/index.mjs | Select-Object LastWriteTime
Get-Item packages/frontend-sdk/src/AuthProvider.tsx | Select-Object LastWriteTime
```

**自己修正コマンド**:
```powershell
Set-Location packages/frontend-sdk; npm run build
Set-Location ../../examples/react-app; Remove-Item -Recurse -Force node_modules/.vite
npm run dev
```

**恒久対策済み**: `examples/react-app/package.json` の `predev` スクリプトが SDK ビルド + Vite キャッシュクリアを自動実行。
`npm run dev` 1コマンドで常に最新状態が起動する。

---

### P4: Keycloak ログイン失敗時に HTTP 500（error ID表示）

**症状**: 誤ったパスワード入力などでログインが失敗すると、エラーメッセージでなく `Error ID xxxxxxxx` が表示される

**根本原因**: カスタムテーマの `theme.properties` に `import=common` があると
`FreeMarkerLoginFormsProvider.createErrorPage` で `ArrayIndexOutOfBoundsException` が発生する。

**診断確認**:
```powershell
Get-Content auth-stack/keycloak/themes/common-auth/login/theme.properties
# ❌ 異常: import=common が存在する
# ✅ 正常: import=common が存在しない
```

**自己修正**: `auth-stack/keycloak/themes/common-auth/login/theme.properties` から `import=common` 行を削除し、Keycloakコンテナのみ再起動（ボリューム削除不要）:
```powershell
docker restart common-auth-keycloak
```

**恒久対策済み**: `theme.properties` から `import=common` を削除済み。

---

### P5: Docker ヘルスチェックが `unhealthy` と表示される（Windows）

**症状**: `docker ps` で Keycloak が `unhealthy` と表示されるが、実際には起動している

**根本原因**: Windows の Docker Desktop ではシェル互換性の問題でヘルスチェックコマンドが失敗する。偽陽性。

**確認コマンド**:
```powershell
Invoke-WebRequest -Uri http://localhost:8080/health/ready -UseBasicParsing | Select-Object StatusCode
# 200 なら正常稼働中（unhealthy 表示は無視してよい）
```

---

### P6: ユーザー管理画面（Admin API）が動作しない

**症状**: React の管理画面でユーザー一覧が表示されない / ネットワークタブで `/api/admin/users` が 401・403・404・500 を返す

**根本原因**: 複数の設定不備が連鎖的に発生する。

| 段階 | エラー | 原因 |
|------|--------|------|
| 404 | `/api/admin/users` が見つからない | `setup.py` の admin router prefix と Vite proxy パスの不一致 |
| 401 | `Audience doesn't match` | `KEYCLOAK_CLIENT_ID` が `backend-app` のままで `example-app` と不一致 / audience mapper 未設定 |
| 500 | `Admin API not configured (KC_ADMIN_CLIENT_SECRET missing)` | `admin-api-client` が Keycloak に未作成 / `.env` に `KC_ADMIN_*` 未設定 / `load_dotenv()` 未呼出 |
| 403 | Keycloak Admin API が Forbidden | `admin-api-client` の `defaultClientScopes` に `roles` が含まれていない |

**診断コマンド**:
```powershell
# 1. Admin router のパスが正しいか
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/common-auth/protocol/openid-connect/token' -Body @{grant_type='password';client_id='example-app';username='admin_acme-corp@example.com';password='admin123'}).access_token
Invoke-RestMethod -Uri 'http://localhost:8000/api/admin/users' -Headers @{Authorization="Bearer $t"} -Method Get
# ✅ 正常: ユーザー一覧 JSON が返る
# ❌ 異常: 404/401/403/500

# 2. audience mapper が設定されているか
$at = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$clients = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/clients' -Headers @{Authorization="Bearer $at"}
$ea = $clients | Where-Object { $_.clientId -eq 'example-app' }
$mappers = Invoke-RestMethod -Uri "http://localhost:8080/admin/realms/common-auth/clients/$($ea.id)/protocol-mappers/models" -Headers @{Authorization="Bearer $at"}
$mappers | Where-Object { $_.protocolMapper -eq 'oidc-audience-mapper' } | Select-Object name
# ✅ 正常: audience-mapper が存在する
# ❌ 異常: 空

# 3. admin-api-client が存在し、roles スコープを持つか
$aac = $clients | Where-Object { $_.clientId -eq 'admin-api-client' }
if ($aac) { Write-Host "admin-api-client exists: $($aac.id)" } else { Write-Host "❌ admin-api-client not found" }

# 4. .env に KC_ADMIN_* が設定されているか
Get-Content examples/fastapi-app/.env | Select-String "KC_ADMIN"
# ✅ 正常: KC_ADMIN_CLIENT_ID=admin-api-client, KC_ADMIN_CLIENT_SECRET=<secret>
```

**恒久対策済み**:
- `setup.py`: admin router prefix を `/api/admin` に修正済み
- `realm-export.json`: `example-app` に `oidc-audience-mapper` 追加済み
- `realm-export.json`: `admin-api-client`（confidential, `roles` スコープ付き, `realm-admin` サービスアカウントロール）追加済み
- `main.py`: `load_dotenv()` を追加して `os.environ.get("KC_ADMIN_*")` が `.env` を読むよう修正済み
- `.env.example`: `KC_ADMIN_CLIENT_ID` / `KC_ADMIN_CLIENT_SECRET` テンプレート追加済み

---

### 起動前セルフチェックリスト

作業開始時に以下を確認すること:

```
[ ] docker ps → 4コンテナ(keycloak, keycloak-db, app-db, mailhog)が起動中
[ ] curl http://localhost:8080/health/ready → HTTP 200
[ ] http://localhost:8025 → MailHog UI 表示
[ ] realm roles マッパーの id.token.claim = true (P1診断コマンドで確認)
[ ] SMTP host = mailhog (P2診断コマンドで確認)
[ ] examples/fastapi-app/.env が存在する（KC_ADMIN_* 含む）
[ ] examples/react-app/.env が存在する
[ ] GET /api/admin/users が 200 を返す (P6診断コマンドで確認)
```

`docker-compose down -v` 後に再起動した場合は **P1・P2・P6 を必ず再診断すること**。
