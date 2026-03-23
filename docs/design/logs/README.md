# Design Logs — 設計会議ログ

`/design` コマンドによる設計会議の**生の議論記録**を保存するディレクトリです。

## ⚠️ ログと正式設計書の役割分担

| 種別 | 場所 | 内容 |
|------|------|------|
| **正式設計書** | `docs/design/*.md`, `docs/design/auth/mfa/*.md` | 設計決定・仕様・構成のみ。実装時に参照する |
| **会議ログ** | `docs/design/logs/*.md`（このディレクトリ） | 議論の経緯・論点・却下理由。意思決定の根拠追跡用 |

### 運用ルール

1. `/design` 実行 → 会議ログをこのディレクトリに保存
2. 設計承認後 → 決定事項を正式設計書に集約（議論形式を除去）
3. 会議ログは削除しない（設計判断の根拠を追跡可能にするため）
4. 正式設計書の末尾に `*元ログ: [リンク]*` を記載して紐付ける

### 正式設計書への昇格基準

- 新しい機能領域の設計決定が含まれている
- 既存の正式設計書に含まれない設計仕様がある
- 複数ファイルに影響するアーキテクチャ決定がある

### 昇格不要（ログのまま残す）

- 既存の正式設計書に既に反映済みの内容
- 初期検討段階で後に撤回・吸収された設計
- 他の設計会議で上書きされた決定

## ファイル命名規則

```
YYYY-MM-DD_HHmmss_<feature>.md   # タイムスタンプ付き
design-NNN-<feature>.md            # 番号付き
```

## ログファイルの構造

```markdown
# 設計会議記録 — <機能名>

## 参加者
PM, Architect, DB Specialist, Security Specialist, Senior Engineer
+ ドメインペルソナ: （設定されている場合）

## 要件サマリー
（PRDからの抜粋）

## 設計決定
（API設計 / DB設計 / セキュリティ設計 / 実装方針）

## 議論のポイント
- 論点1: ...（誰がどう主張し、どう決着したか）

## 起票すべきADR
- ADR-XXX: タイトル

## 次のアクション
- [ ] 正式設計書への反映
- [ ] ADR起票
- [ ] 設計レビュー実施
```

## 現在のファイル一覧

| ファイル | 内容 | 正式設計書への反映 |
|---------|------|------------------|
| `2026-02-28_100000_user-authentication.md` | 初期認証設計（Keycloak採用前） | `architecture.md` に吸収済み |
| `2026-03-01_163700_auth-module.md` | コアアーキテクチャ設計 | → `architecture.md` |
| `2026-03-01_190131_phase2-features.md` | Phase 2機能設計 | → `backend-sdk-details.md` + `frontend-sdk-details.md` |
| `2026-03-01_phase3-user-management.md` | ユーザー管理・RBAC | → `user-management.md` |
| `2026-03-01_saas-multitenant.md` | マルチテナント設計 | → `multi-tenant.md` |
| `design-001-mfa.md` | MFA基盤インフラ | → `auth/mfa/infrastructure.md` |
| `design-002-tenant-mfa-policy.md` | テナントMFAポリシー | → `auth/mfa/tenant-policy.md` |
