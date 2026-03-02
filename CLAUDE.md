# CLAUDE.md — AI Autonomous Development Environment

このファイルはAIエージェントがプロジェクトを理解するためのエントリーポイントです。

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
| `/re-review` | 修正後の再レビュー |

### Git操作

| コマンド | 動作 |
|----------|------|
| `/push` | APPROVE後にコミット＆プッシュ |
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
要件定義 → 分類判断 → [Standard/Major] → /design → /implement → 実装（TDD）
                  └→ [Hotfix/Minor] ──────────────────────────→ 即実装

実装後: /review → /fix → /re-review → /push
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

## トークン効率化

品質を維持しながらトークン消費を抑えるための仕組み:

### 階層化レビュー

```
Level 1: 自動チェック（リンター + テスト）→ 問題なければ完了
Level 2: 簡易レビュー（1視点でクイックチェック）
Level 3: 詳細レビュー（5人専門家、重要な変更時のみ）
```

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
