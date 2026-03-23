# Review Log — 設計レビュー（common-auth）

## メタデータ
- 日時: 2026-03-01 16:37:00
- 対象: 設計ドキュメント一式（PRD, API, DB, ADR x5）
- レビュアー: Review Board（5人合議制）+ 認証基盤テックリード
- ラウンド: 1

## レビュー対象

設計ドキュメント:
- `docs/prd/prd.md` — プロダクト要件定義
- `docs/api/openapi.yaml` — Backend SDK API仕様（3エンドポイント）
- `docs/db/schema.sql` — 業務DBスキーマ（tenants, user_profiles + RLS）
- `docs/adr/001-keycloak-as-idp.md`
- `docs/adr/002-oidc-authorization-code-flow-pkce.md`
- `docs/adr/003-multi-tenant-realm-isolation.md`
- `docs/adr/004-pyjwt-for-backend-jwt-verification.md`
- `docs/adr/005-oidc-client-ts-for-frontend.md`
- `docs/review/persona.md` — ドメインペルソナ

## Phase 1: 初見ラウンド

**PM**: PRDのMVP機能定義は明確。ただし、`FR-006: Backend SDK`と`FR-007: Docker Compose構成`の受入基準が抽象的。具体的に"どこまでできればMVP完了か"の定義が必要。例えば、Backend SDKのパッケージ公開先（TestPyPI or 社内PyPI）や、Docker Composeの可搬性検証（3つの異なる環境でデプロイ確認）などを追記すべき。

**Arch**: 全体アーキテクチャは優れている。特にAuth StackとSDK Layerの完全分離、OIDC標準準拠によるポータビリティは評価する。懸念点は**JWKS公開鍵キャッシュの障害時の挙動**。ADR-004でTTL 24h+未知kid即時refreshと記載があるが、KeycloakがダウンしたときのGraceful Degradation戦略がない。既存キャッシュを延長利用するのか、即時エラーにするのか、API仕様書に明記が必要。

**Eng**: Backend SDKの最小コード例（`AuthConfig.from_env()` + `setup_auth()`）は開発者DXが良い。一方、**エラーハンドリングの方針が不明確**。例えばJWT検証失敗時に401を返すのは自明だが、Keycloak接続失敗時は503か502か？OpenAPI仕様では`/auth/health`が503を返すと定義されているが、通常のエンドポイントでの認証ミドルウェア障害時の挙動が未定義。

**Sec**: セキュリティ設計は堅牢。Authorization Code Flow + PKCE、RS256、SecurityHeadersミドルウェアは適切。**致命的な問題を1点発見**: `docs/db/schema.sql`のRLSポリシーがコメントアウトされており、マルチテナント環境でデータ分離が強制されていない。アプリケーション側のミドルウェア実装にバグがあった場合、テナント間データ漏洩が発生する。RLSをデフォルト有効にするか、無効にする場合の明確なリスク説明と運用ガイドラインが必要。

**DB**: `user_profiles`テーブルの設計は良い。`tenant_id`外部キー、Unique Index (`tenant_id`, `email`) も適切。**1点気になるのは`roles TEXT[]`カラム**。PostgreSQL配列型は柔軟だが、ロール定義が正規化されていない。将来的にロールベースのアクセス制御を強化する場合、`roles`テーブルと`user_roles`中間テーブルへの移行が必要になる。Phase 1では許容するが、ADRまたはDB設計書に"簡易的な実装であり、将来的に正規化する可能性"を記載すべき。

## Phase 2: 議論

**Arch**: Secの指摘は重要。RLSを無効にする場合、ミドルウェアの`tenant_id`フィルタリングロジックの品質が全てを決める。Backend SDKのテストで、**テナント分離が破られないことの自動テスト**を必須にすべき。

**Sec**: Archに同意。さらに、設計書レベルで"Defense in Depth"の原則を明記したい。ミドルウェアでフィルタリング + RLSで二重チェックの構成を推奨とし、RLS無効は顧客判断とする。無効化時のリスク（コードバグ、ORMバイパス時のデータ漏洩）をドキュメント化する。

**DB**: Secの提案に賛成。RLSの有効化をデフォルトとし、`schema.sql`のコメントアウトを外す。ただし、Backend SDKでセッション設定（`SET app.current_tenant_id`）を確実に行うドキュメントとコード例が必要。

**PM**: Engの指摘（エラーハンドリング未定義）は開発者DXに直結する。Backend SDKのREADMEまたはAPI仕様書に"エラーレスポンス一覧表"を追加すべき。特にKeycloak障害時、JWKS取得失敗時、トークン有効期限切れ時の挙動を明示。

**Eng**: PMの提案に同意。加えて、**設定バリデーション**も重要。`AuthConfig.from_env()`で環境変数が不足している場合、起動時に明確なエラーメッセージを出すべき。"KEYCLOAK_URL is required"のような具体的な指示が必要。

**Arch**: PMの最初の指摘（MVP受入基準の曖昧さ）も重要。PRDに"Definition of Done"セクションを追加し、各機能の完了条件を明記すべき。特にSDKのパッケージ配布については、社内利用なのかOSS公開なのかで作業範囲が変わる。

**DB**: rolesカラムの正規化について補足。Phase 1では`TEXT[]`で進めるが、ADR-003（マルチテナント分離）に"ロール管理の簡易実装"として記録し、Phase 3での正規化を明記すべき。

## Phase 3: 判定

**判定: REQUEST_CHANGES 🔄**

### [MUST FIX]

1. **`docs/db/schema.sql`**: RLSポリシーのコメントアウトを外し、デフォルト有効化する。Backend SDKでの`SET app.current_tenant_id`設定を必須ドキュメント化
2. **`docs/api/openapi.yaml`**: エラーレスポンス仕様を追加。Keycloak障害時（503）、JWT検証失敗時（401）、設定不備時（500）の挙動を明記
3. **`docs/prd/prd.md`**: 各機能の"Definition of Done"を追加（特にFR-005, FR-006のSDK配布範囲とパッケージ公開先）

### [SHOULD FIX]

4. **ADR新規起票**: "RLSによるDefense in Depthの採用"（RLS有効化判断、無効化時のリスク、テナント分離テスト戦略を記載）
5. **`docs/adr/004-pyjwt-for-backend-jwt-verification.md`**: JWKS取得失敗時のGraceful Degradation戦略を追記（既存キャッシュ延長利用 or 即時エラー）
6. **Backend SDK設計補足**: 環境変数バリデーション（起動時の明確なエラーメッセージ）とエラーハンドリングガイドラインをドキュメント化

### [CONSIDER]

7. **`docs/db/schema.sql`**: `roles TEXT[]`の設計判断をコメントに記載（Phase 3での正規化予定を明記）
8. **ADR-003更新**: ロール管理の簡易実装について補足
9. **PRD**: 非機能要件に「テナント分離の自動テスト」を追加

### [GOOD]

- Auth StackとSDK Layerの完全分離によるポータビリティ設計
- OIDC標準準拠によるIdP非依存の設計（将来の移行容易性）
- Lazy Syncのオプトイン化（業務DB不要プロジェクトへの配慮）
- 5つのADRによる技術選定の透明性

## 次のステップ

`/fix` で指摘事項を修正してください。

---

## 修正記録

修正日時: 2026-03-01 16:45:00
実施者: AI Agent

### 修正内容

**[MUST FIX]**
- ✅ #1: `docs/db/schema.sql` — RLSポリシーのコメントアウトを外し、デフォルト有効化。Backend SDKでの`SET app.current_tenant_id`設定方法をコメントに記載、rolesカラムの設計判断も追記
- ✅ #2: `docs/api/openapi.yaml` — エラーレスポンス仕様表を追加。Keycloak障害時（503）、JWT検証失敗時（401）、設定不備時（500）の挙動を明記。JWKS Graceful Degradation戦略も記載
- ✅ #3: `docs/prd/prd.md` — Section 8「Definition of Done」を追加。各機能（FR-001〜009）の完了条件を具体的に定義

**[SHOULD FIX]**
- ✅ #4: `docs/adr/006-defense-in-depth-rls.md` — 新規ADR起票。RLS有効化判断、無効化時のリスク、テナント分離テスト戦略を記載
- ✅ #5: `docs/adr/004-pyjwt-for-backend-jwt-verification.md` — JWKS取得失敗時のGraceful Degradation戦略を追記（状況別の挙動表を追加）
- ✅ #6: `docs/design/backend-sdk-details.md` — Backend SDK設計補足ドキュメントを新規作成。環境変数バリデーション、エラーハンドリング、RLSセッション設定、ロギング戦略を詳述

**[CONSIDER]（今回対応）**
- ✅ #7: `docs/db/schema.sql` — rolesカラムの設計判断をコメントに記載（MUST FIX #1に含めて対応）
- （#8, #9は次回レビュー時に検討）

### 未対応
なし（MUST FIX・SHOULD FIXすべて完了）

---

## 再レビュー

再レビュー日時: 2026-03-01 16:50:00
ラウンド: 2

### 前回の指摘（解決確認）

**[MUST FIX]**
- ✅ #1: RLSポリシー有効化 — 完全解決。Defense in Depthの説明、SET LOCAL前提条件、無効化リスク、rolesカラム設計判断すべて記載
- ✅ #2: エラーレスポンス仕様追加 — 完全解決。HTTPステータスとエラーコードの対応表、Graceful Degradation戦略、設定バリデーションエラー例すべて記載
- ✅ #3: Definition of Done追加 — 完全解決。FR-001〜009の具体的完了条件、SDK配布先、可搬性検証環境を明記

**[SHOULD FIX]**
- ✅ #4: Defense in Depth ADR起票 — 完全解決。ADR-006作成、2層防御図解、リスクシナリオ表、テナント分離テスト例を含む高品質なADR
- ✅ #5: JWKS障害時戦略追記 — 完全解決。ADR-004に状況別挙動表を追加、可用性とセキュリティのバランス考慮
- ✅ #6: Backend SDK設計補足 — 完全解決。backend-sdk-details.md作成、環境変数バリデーション、エラーハンドリング、RLS設定、ロギング戦略を網羅

### 新規指摘

**[CONSIDER]（実装フェーズで対応）**
1. ADR-006のテナント分離テストコード例を、`examples/tests/`にサンプル実装として提供
2. Backend SDKのロギング設定方針を明確化（SDK提供 vs 利用者設定）

### レビューボードの総評

**PM**: すべてのMUST FIXが解決され、MVPの完了条件が明確になった。実装フェーズに進める。

**Arch**: 設計ドキュメント間の整合性が保たれており、ポータビリティ要件を満たす設計が完成した。

**Eng**: Backend SDK設計補足ドキュメントにより、実装時の判断基準が明確になった。

**Sec**: Defense in DepthによるRLS強制により、セキュリティ要件を満たしている。

**DB**: スキーマ設計、RLS設定、データ分離戦略すべて適切。

### 最終判定: APPROVE ✅

設計レビュー完了。実装計画会議（`/implement`）に進んでください。
