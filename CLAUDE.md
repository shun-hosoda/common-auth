# CLAUDE.md — AI Autonomous Development Environment

このファイルはAIエージェントがプロジェクトを理解するためのエントリーポイントです。

## プロジェクト構造

```
.
├── .cursor/
│   ├── rules/                # AIの行動ルール
│   │   ├── core_rules.mdc        # 基本原則（設計第一、ADR駆動）
│   │   ├── commands.mdc          # スラッシュコマンド定義
│   │   ├── review_process.mdc    # レビューサイクル制御
│   │   ├── autonomous_workflow.mdc # 自律開発ワークフロー
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
│       └── db-specialist/        # スキーマ・クエリ最適化
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

### 設計・実装フェーズ

| コマンド | 動作 |
|----------|------|
| `/design` | 5人専門家による設計会議（API/DB/セキュリティ設計） |
| `/design <機能名>` | 特定機能の設計会議 |
| `/implement` | 5人専門家による実装計画会議（TDD計画、実装順序） |
| `/implement <機能名>` | 特定機能の実装計画 |

### レビュー・修正フェーズ

| コマンド | 動作 |
|----------|------|
| `/review` | 5人専門家レビューボード会議を開催 |
| `/review --pr` | PRの差分をレビュー |
| `/review --staged` | ステージ済み変更をレビュー |
| `/review --design` | 設計書をレビュー |
| `/review <ファイル>` | 特定ファイルをレビュー |
| `/fix` | レビュー指摘（MUST/SHOULD FIX）を修正 |
| `/re-review` | 修正後の再レビュー |

### Git操作フェーズ

| コマンド | 動作 |
|----------|------|
| `/push` | APPROVE後にコミット＆プッシュ |
| `/comment` | レビュー結果をPRコメントとして投稿 |
| `/comment <msg>` | 任意のコメントをPRに投稿 |

## 開発フロー

```
要件定義 → /design → /implement → 実装（TDD） → /review → /fix → /re-review → /push
            ↓          ↓                          ↑                    │
            設計書     実装計画                    └────────────────────┘
            更新       記録
```

### フェーズ詳細

1. **要件定義**: `docs/prd/prd.md` に要件を記入
2. **設計会議**: `/design` で5人専門家が議論 → API/DB設計を確定
3. **実装計画**: `/implement` でTDD計画と実装順序を決定
4. **実装**: TDDサイクル（Red → Green → Refactor）
5. **レビュー**: `/review` で5人専門家が差分レビュー
6. **修正**: `/fix` で指摘事項を修正
7. **再レビュー**: `/re-review` で修正結果を検証
8. **プッシュ**: `/push` でAPPROVE後にコミット＆プッシュ

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
