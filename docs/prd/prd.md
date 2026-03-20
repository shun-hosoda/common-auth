# Product Requirement Document (PRD)

## 1. 概要 (Overview)

| 項目 | 内容 |
|------|------|
| プロダクト名 | common-auth（ポータブル認証プラットフォーム） |
| バージョン | 1.0.0 |
| ステータス | Draft |
| 作成日 | 2026-03-01 |
| 更新日 | 2026-03-01 |

### 1.1 背景と課題

- 社内の複数プロジェクトで認証・ユーザー管理を個別実装しており、品質・セキュリティにばらつきがある
- 特定クラウド（AWS Cognito, Azure AD B2C等）に依存すると、顧客環境ごとに認証基盤を変更する必要が生じる
- 認証ロジックの自前実装はセキュリティリスクが高く、メンテナンスコストも大きい

### 1.2 目的

- **Don't Roll Your Own Auth**: 実績あるOSS（Keycloak）を採用し、認証ロジックを自前実装しない
- **ポータブル**: AWS/Azure/GCP/オンプレミスを問わず、Docker Composeで「どこでも動く」認証基盤を提供する
- **再利用可能**: Frontend SDK（React Hooks）とBackend SDK（Python Middleware）としてパッケージ化し、プロジェクト横断で利用可能にする

## 2. ターゲットユーザー

| ペルソナ | 説明 | 主な利用シーン |
|----------|------|----------------|
| アプリ開発者 | 自社プロジェクトにログイン機能を組み込みたい開発者 | SDK導入、API連携 |
| インフラ管理者 | 顧客環境にAuth Stackをデプロイ・運用する担当者 | Docker Compose起動、Realm設定 |
| エンドユーザー | 業務アプリにログインして利用する最終利用者 | ログイン、MFA設定、パスワードリセット |
| テナント管理者 | 自テナントのユーザーを管理する管理者 | ユーザー招待、権限設定 |

## 3. 機能要件 (Functional Requirements)

### 3.1 MVP（Phase 1）

| ID | 機能 | 優先度 | 説明 |
|----|------|--------|------|
| FR-001 | ログイン/ログアウト | Must | OIDC Authorization Code Flow + PKCEによる認証 |
| FR-002 | JWT署名検証 | Must | RS256によるバックエンドでのトークン検証ミドルウェア |
| FR-003 | セキュリティヘッダ付与 | Must | HSTS, CSP, X-Frame-Options等の強制付与ミドルウェア |
| FR-004 | テナント識別 | Must | JWTクレームからのtenant_id抽出とDBクエリフィルタリング |
| FR-005 | Frontend SDK | Must | React Hooks（useAuth, AuthProvider, AuthGuard） |
| FR-006 | Backend SDK | Must | FastAPIミドルウェア・Dependencies（JWT検証、テナント抽出） |
| FR-007 | Docker Compose構成 | Must | Keycloak + PostgreSQL（Keycloak用）のコンテナ構成 |
| FR-008 | Realm設定管理 | Must | JSON Export/Importによる設定のポータビリティ |
| FR-009 | 環境変数設定 | Must | .envによる環境差異の吸収（SMTP、DB接続等） |

### 3.2 MVP（Phase 2）

| ID | 機能 | 優先度 | 説明 |
|----|------|--------|------|
| FR-010 | 二段階認証 (MFA) | Should | Keycloak標準のTOTP（Google Authenticator等）対応 |
| FR-011 | パスワードリセット | Should | セルフサービスのパスワード再設定（Email連携） |
| FR-012 | ユーザーセルフ登録 | Should | メールアドレス確認プロセスを含む新規登録 |
| FR-013 | Rate Limiting | Should | IPベースのリクエスト制限ミドルウェア |

### 3.3 Phase 3: ユーザー管理・アクセス制御

#### 3.3.1 ロールと権限モデル

| ロール | 説明 | できること |
|--------|------|-----------|
| super_admin | システム全体の管理者 | クライアント（テナント）登録・管理、全ユーザー管理 |
| tenant_admin | 特定クライアントの管理者 | 自テナントのユーザー登録・編集・無効化 |
| user | 一般ユーザー | ログイン、プロフィール閲覧、MFA設定、パスワードリセット |

#### 3.3.2 画面遷移

| 状態 | 遷移先 |
|------|--------|
| ログイン済み | `/dashboard` |
| 未ログイン | `/login`（ログイン画面） |
| ログアウト | `/login`（ログイン画面） |

| ID | 機能 | 優先度 | 説明 |
|----|------|--------|------|
| FR-020 | ダッシュボード画面 | Must | ログイン済みユーザーのみアクセス可能 |
| FR-021 | ログイン画面 | Must | 未認証ユーザーのエントリーポイント。Keycloakログイン画面へリダイレクト |
| FR-022 | ログアウト | Must | セッション破棄→ログイン画面へリダイレクト |
| FR-023 | クライアント（テナント）管理 | Must | super_adminのみ。クライアント登録・編集・無効化 |
| FR-024 | ユーザー管理画面 | Must | tenant_adminのみ表示。自テナントのユーザー一覧・登録・編集 |
| FR-025 | ユーザー登録・編集 | Must | tenant_adminがKeycloak Admin API経由でユーザーを作成・編集 |
| FR-026 | ロールベースUI制御 | Must | userロールはユーザー管理画面を表示しない |
| FR-027 | Keycloak UIへの委譲 | Should | ユーザー一覧・登録・編集をKeycloak管理UIに遷移（カスタムテーマ対応可） |

### 3.4 Phase 3.5: テナントMFAポリシー管理

#### 3.4.1 概要

テナント管理者（`tenant_admin`）が自テナント全体のMFA（多要素認証）の有効/無効およびMFA方式を管理画面から設定できるようにする。サイドナビに「セキュリティ設定」画面を追加し、将来的なセキュリティポリシー拡張の受け皿とする。

#### 3.4.2 ユーザーストーリー

| # | ペルソナ | ストーリー | 受入条件 |
|---|---------|-----------|---------|
| US-1 | テナント管理者 | セキュリティ設定画面でテナント全体のMFAを有効にしたい | トグルONでテナント配下の全ユーザーの次回ログインからMFAが要求される |
| US-2 | テナント管理者 | MFA方式をTOTPまたはメールOTPから選択したい | ラジオボタンで方式を選択し保存できる。方式変更時は既存のMFAクレデンシャルがリセットされる旨の確認ダイアログが表示される |
| US-3 | テナント管理者 | MFAを無効にして全ユーザーのMFA要求を解除したい | トグルOFFでMFA要求が解除される。既存のMFAクレデンシャルは保持（再有効化時に再利用可能） |
| US-4 | エンドユーザー | MFA有効テナントにログインした際、指定された方式でMFA設定を求められたい | 初回: MFA登録フロー → 2回目以降: MFAコード入力 |
| US-5 | 一般ユーザー | セキュリティ設定画面にアクセスできないこと | `user`ロールではサイドナビに「セキュリティ設定」が表示されない |
| US-6 | エンドユーザー | ダッシュボードで自分のMFA設定状態を確認し、必要に応じてMFA設定を変更したい | MFAステータスカードが表示され、Keycloak Account Consoleへ遷移してMFA管理が可能 |

#### 3.4.3 機能要件

| ID | 機能 | 優先度 | 説明 |
|----|------|--------|------|
| FR-030 | セキュリティ設定画面 | Must | `tenant_admin`のみアクセス可能。サイドナビに「セキュリティ設定」として追加 |
| FR-031 | MFA有効/無効トグル | Must | テナント全体のMFA強制をON/OFFするトグルスイッチ |
| FR-032 | MFA方式選択 | Must | TOTP（認証アプリ）またはメールOTPのいずれかを選択。ラジオボタンUI |
| FR-033 | MFA設定取得API | Must | `GET /api/admin/security/mfa` — 現在のMFA設定を返す |
| FR-034 | MFA設定更新API | Must | `PUT /api/admin/security/mfa` — MFA有効/無効・方式を更新 |
| FR-035 | 方式変更時の確認 | Must | MFA方式を変更する場合、既存クレデンシャルリセットの確認ダイアログ表示 |
| FR-036 | MFA強制ログインフロー | Must | MFA有効テナントのユーザーログイン時にKeycloak認証フローでMFAを要求 |
| FR-037 | MFA設定の永続化 | Must | MFA設定をKeycloakグループ属性（`mfa_enabled`, `mfa_method`）として保存 |

#### 3.4.4 画面仕様

```
/security — セキュリティ設定画面（tenant_adminのみ）
┌─────────────────────────────────────────────┐
│ [SideNav]  │  セキュリティ設定               │
│            │                                 │
│ ダッシュボード │  ┌─ MFA（多要素認証）──────┐  │
│ ユーザー管理  │  │                          │  │
│ ★セキュリティ │  │  MFA を有効にする [●ON]  │  │
│ 設定        │  │                          │  │
│            │  │  MFA方式:                 │  │
│            │  │  ○ TOTP（認証アプリ）     │  │
│            │  │    Google Authenticator等  │  │
│            │  │  ○ メールOTP             │  │
│            │  │    ログイン時にメールで     │  │
│            │  │    ワンタイムコードを送信   │  │
│            │  │                          │  │
│            │  │  [保存]                   │  │
│            │  └──────────────────────────┘  │
└─────────────────────────────────────────────┘
```

#### 3.4.5 API仕様

**GET /api/admin/security/mfa**

レスポンス:
```json
{
  "mfa_enabled": true,
  "mfa_method": "totp"
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| `mfa_enabled` | boolean | MFA強制の有効/無効 |
| `mfa_method` | string | `"totp"` または `"email"` |

**PUT /api/admin/security/mfa**

リクエスト:
```json
{
  "mfa_enabled": true,
  "mfa_method": "email"
}
```

レスポンス: `200 OK`
```json
{
  "status": "updated",
  "mfa_enabled": true,
  "mfa_method": "email"
}
```

#### 3.4.6 技術方針

| 項目 | 方針 |
|------|------|
| MFA設定の保存先 | Keycloakグループ属性（`mfa_enabled`, `mfa_method`）。ADR-003の共有Realm+Groupsモデルに準拠 |
| MFA強制の実現方法 | Keycloak認証フローのConditional OTP + グループ属性による条件分岐 |
| TOTP | Keycloak標準OTP Authenticator。アルゴリズム: HMAC-SHA1 / 6桁 / 30秒 |
| メールOTP | Keycloak v24標準Email OTP Authenticator。OTP有効期限: 5分 / 試行上限: 3回 |
| 方式切替時 | 既存ユーザーのOTPクレデンシャルを一括リセット（Admin API経由）。次回ログインで新方式のMFA登録を促す |
| 認証フロー構成 | `browser` → `Username/Password` → `Conditional OTP Subflow`（グループ属性で分岐） |
| Backend API | `KeycloakAdminClient` にグループ属性のCRUDメソッドを追加 |
| Frontend | 新規 `SecuritySettings.tsx` ページ。共有 `SideNav` に `NavItem` を追加 |

#### 3.4.7 制約・注意事項

- MFA方式の変更は即座に反映されるが、既にログイン済みのセッションには影響しない（次回ログインから適用）
- メールOTPはKeycloak v24以降が必須（`realm-export.json` の `authenticationFlows` に Email OTP Authenticator が定義されていること）
- テナント単位の認証フロー切替はKeycloakのConditional Authenticatorで実現する（Realm-level flow自体は1つ）
- `super_admin` もセキュリティ設定画面にアクセス可能（全テナントの設定を閲覧・変更できる）

### 3.5 将来的な拡張（Phase 4+）

| ID | 機能 | 説明 |
|----|------|------|
| FT-001 | ソーシャルログイン | Google, Microsoft Entra ID連携（Keycloak設定変更のみ） |
| FT-002 | クラウドマネージド移行 | AWS Cognito等への移行パス（OIDC準拠のため） |
| FT-003 | 監査ログ | ログイン履歴、権限変更の記録・可視化 |
| FT-004 | パスワードポリシー設定 | セキュリティ設定画面にパスワード強度・有効期限ポリシーを追加 |
| FT-005 | セッションタイムアウト設定 | セキュリティ設定画面にセッション有効期限の設定を追加 |
| FT-006 | 信頼済みデバイス（Cookie） | MFA認証後に信頼済みデバイスCookieを発行し、一定期間MFAをスキップ |

## 4. 非機能要件 (Non-Functional Requirements)

| カテゴリ | 要件 | 目標値 |
|----------|------|--------|
| パフォーマンス | JWT検証レスポンスタイム | < 10ms (p95) |
| パフォーマンス | ログインフロー完了時間 | < 3s (Keycloak含む) |
| 可用性 | Keycloak稼働率 | 99.9% |
| セキュリティ | 認証方式 | OIDC Authorization Code Flow + PKCE |
| セキュリティ | トークン署名 | RS256 (RSA 2048bit以上) |
| ポータビリティ | デプロイ環境 | Docker対応の任意環境 |
| スケーラビリティ | 同時接続数 | 1,000+ (Keycloakクラスタリングで拡張可能) |

## 5. 制約事項

- クラウド固有のマネージドサービスに依存しない（Dockerコンテナのみ）
- 認証ロジックは自前実装しない（Keycloak + OIDC標準プロトコルを使用）
- パスワード等の認証情報は業務DBに保持しない（Keycloakに一元管理）
- Python 3.11+、React 18+を対象

## 6. 成功指標 (KPIs)

| 指標 | 目標値 | 測定方法 |
|------|--------|----------|
| 新規プロジェクトへの導入時間 | < 1日 | SDK導入からログイン動作確認まで |
| セキュリティ脆弱性 | 0件 (Critical/High) | OWASP ZAP, Dependabot |
| プロジェクト横断利用率 | 3プロジェクト以上 | 導入プロジェクト数 |

## 7. マイルストーン

| フェーズ | 内容 | 期限 |
|----------|------|------|
| Phase 1 | MVP: Auth Stack + Frontend/Backend SDK | ✅ 完了 |
| Phase 2 | MFA, パスワードリセット, セルフ登録, Rate Limiting | ✅ 完了 |
| Phase 3 | ユーザー管理UI, ロールベースアクセス制御, Keycloakテーマ | ✅ 完了 |
| Phase 3.5 | テナントMFAポリシー管理（セキュリティ設定画面） | TBD |
| Phase 4+ | ソーシャルログイン, 監査ログ, パスワードポリシー | TBD |

## 8. Definition of Done（完了条件）

各機能の完了基準を定義する。

### FR-001〜004: 認証フロー・JWT検証・セキュリティヘッダ・テナント識別
- [ ] OIDC Authorization Code Flow + PKCEの動作確認（手動テスト）
- [ ] JWT署名検証の単体テスト（有効/無効/期限切れケース）
- [ ] セキュリティヘッダがレスポンスに含まれることを確認
- [ ] tenant_id抽出とDBフィルタリングの統合テスト
- [ ] テナント分離の自動テスト（テナントAのユーザーがテナントBのデータにアクセスできないこと）

### FR-005: Frontend SDK
- [ ] npm パッケージとして公開（スコープ: `@common-auth/react`）
- [ ] 公開先: npmjs.com（パブリック）または社内npm registry
- [ ] READMEに導入手順・最小コード例を記載
- [ ] TypeScript型定義を含む
- [ ] サンプルアプリで動作確認（`examples/react-app/`）

### FR-006: Backend SDK
- [ ] PyPI パッケージとして公開（パッケージ名: `common-auth`）
- [ ] 公開先: pypi.org（パブリック）または社内PyPI
- [ ] READMEに導入手順・最小コード例を記載
- [ ] 型ヒント（Type Hints）を含む
- [ ] サンプルアプリで動作確認（`examples/fastapi-app/`）
- [ ] 起動時の環境変数バリデーション実装（不足時に明確なエラーメッセージ）

### FR-007: Docker Compose構成
- [ ] `auth-stack/docker-compose.yml` で Keycloak + PostgreSQL が起動
- [ ] `.env.example` で必須環境変数を明示
- [ ] 3つの異なる環境での可搬性検証:
  - Windows（Docker Desktop）
  - macOS（Docker Desktop）
  - Linux（Ubuntu 22.04 + Docker Engine）
- [ ] Realm設定のJSON Export/Import動作確認

### FR-008: Realm設定管理
- [ ] テンプレートRealm設定（`keycloak/realm-export.json`）を提供
- [ ] Import手順をドキュメント化

### FR-009: 環境変数設定
- [ ] `.env.example` に全設定項目を記載
- [ ] 環境差異の吸収確認（SMTP設定、DB接続、Keycloak URL）
