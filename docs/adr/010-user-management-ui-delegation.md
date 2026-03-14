# ADR-010: ユーザー管理UI実装方針

## ステータス

**Superseded** (2026-03-14) — カスタムReact実装（Option A）に方針変更

> 初版 (2026-03-01): Keycloak管理コンソール委譲（Option B）を採用
> 改訂 (2026-03-14): 以下の理由によりOption A（カスタムReact + Backend Admin API）へ変更

## コンテキスト

Phase 3でtenant_adminによるユーザー管理機能を実装するにあたり、UIの実装方針を決定する必要があった。

### 選択肢

**Option A: カスタムReact実装**
- Backend Admin APIラッパーを実装し、React UIでユーザー一覧・CRUD操作を提供
- 利点: フルコントロール、UIの一貫性、テナント境界の厳密な制御
- 欠点: 実装工数が大きい（Backend API + React UIで推定2〜3週間）

**Option B: Keycloak管理コンソール委譲**
- ユーザー管理操作をKeycloak管理コンソールのURLへリダイレクト
- 利点: 実装工数少（数時間）、Keycloakの豊富な機能をそのまま活用
- 欠点: UIカスタマイズに制限あり、テナント境界チェックが不十分

## 決定

**Option A（カスタムReact + Backend Admin API）を採用する。**

### 変更理由

1. **UXの最適化**: 顧客が必要な機能（ユーザー追加・編集・削除、MFAリセット等）だけに絞ったシンプルなUIを提供できる
2. **データ統合**: 自前DBに保存された業務データ（部署名、役職等）とKeycloakのユーザー情報を統合した一覧表を実現できる
3. **UIの一貫性**: アプリ本体と同じデザインシステムで構築でき、Keycloak管理コンソールへの遷移による違和感を排除
4. **テナント境界の厳格な制御**: Backend APIで`tenant_id`フィルタリングを強制し、A社管理者がB社ユーザーにアクセスできない設計を担保

### 実装方針

**Backend（Python / FastAPI）:**
- Keycloak Admin REST APIをプロキシするAPIエンドポイントを実装
- ミドルウェアでJWTの`realm_access.roles`に`tenant_admin`が含まれることを検証
- `tenant_id`クレームによるテナント境界チェックを全APIで強制

**Frontend（React）:**
- `/admin/users` に自作のユーザー管理画面を実装
- Backend Admin API経由でKeycloakを操作（フロントから直接Admin APIは叩かない）
- PC/SP対応のレスポンシブUIを提供

### セキュリティ要件（必須）

1. **管理画面の認可**: JWTの`realm_access.roles`に`tenant_admin`以上のロールが含まれることをBackendミドルウェアで検証
2. **テナント境界チェック**: リクエスト対象ユーザーの`tenant_id`がJWT内の`tenant_id`と一致することを検証。super_adminのみ全テナントアクセス可
3. **フロントのロール制御はUIのみ**: セキュリティの正本はBackend API側。フロントの`hasRole()`チェックはUI制御目的のみ

## 影響

- Backend SDKへのAdmin APIラッパーの追加が必要
- フロントエンドにユーザー管理画面のフル実装が必要
- UIの一貫性とテナント分離の品質が大幅に向上
- 実装工数は増加するが、長期的な保守性とカスタマイズ性に優れる
