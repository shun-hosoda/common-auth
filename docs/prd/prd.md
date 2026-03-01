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

### 3.3 将来的な拡張（Phase 3+）

| ID | 機能 | 説明 |
|----|------|------|
| FT-001 | ソーシャルログイン | Google, Microsoft Entra ID連携（Keycloak設定変更のみ） |
| FT-002 | クラウドマネージド移行 | AWS Cognito等への移行パス（OIDC準拠のため） |
| FT-003 | Keycloak Admin API ラッパー | ユーザー管理APIの提供（管理者向け） |
| FT-004 | 監査ログ | ログイン履歴、権限変更の記録・可視化 |

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
| Phase 1 | MVP: Auth Stack + Frontend/Backend SDK | TBD |
| Phase 2 | MFA, パスワードリセット, セルフ登録 | TBD |
| Phase 3 | ソーシャルログイン, 監査ログ | TBD |

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
