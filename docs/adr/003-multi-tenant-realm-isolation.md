# ADR-003: マルチテナント分離方式（Shared Realm + Groups + User Attribute）

## ステータス

改訂済み（2026-03-01） ※ 初版「Realm per tenant」から変更

## コンテキスト

common-authはSaaS BtoB向けマルチテナントプラットフォームとして設計する。
1つのKeycloakインスタンス・1つのRealmで複数の企業テナントを収容し、
業務DBのRLSでデータを分離する。

## 決定

**Shared Realm + Keycloak Groups + User Attribute** 方式を採用する。

### テナント構造

```
Keycloak Realm: common-auth（全テナント共有）
│
├── Groups
│   └── /tenants/{tenant_id}   ← 1グループ = 1テナント（企業）
│
├── User Attribute: tenant_id = "{tenant_id}"   ← JWTへの埋め込みに使用
│
└── Client Scope: tenant（Protocol Mapper）
    └── User Attribute → JWT claim "tenant_id"
```

### tenant_id の流れ

```
super_admin がテナント登録
 → Keycloak Group /tenants/acme-corp を作成
 → ユーザーをグループに追加
 → User Attribute: tenant_id = "acme-corp" を設定

ユーザーがログイン
 → Keycloakが JWT に tenant_id = "acme-corp" を埋め込む（Protocol Mapper）

バックエンドがリクエストを受信
 → JWT から tenant_id を取得（TENANT_ID_SOURCE=custom, TENANT_ID_CLAIM=tenant_id）
 → PostgreSQL RLS: SET LOCAL app.tenant_id = 'acme-corp'
 → 業務DBクエリが自テナントのデータのみを返す
```

## 選択肢と比較

| 方式 | 採用 | 理由 |
|------|------|------|
| Realm per tenant | ❌ 非採用 | SaaSでは管理オーバーヘッドが大きすぎる。テナント100社 = 100Realm |
| Keycloak Organizations（v26+） | ❌ 非採用 | 新機能で安定性・ドキュメントが不十分 |
| Groups + Script Mapper | ❌ 非採用 | Keycloak 18+でScriptMapperがデフォルト無効 |
| **Groups + User Attribute** | ✅ 採用 | Groups=管理可視化、Attribute=JWT埋め込みが標準機能で確実 |

## Backend SDK設定

```env
# SaaS BtoB向け設定
TENANT_ID_SOURCE=custom
TENANT_ID_CLAIM=tenant_id
```

## ロール設計

| ロール | 対象 | 権限 |
|--------|------|------|
| `super_admin` | SaaS運営者 | テナント（Group）作成・全ユーザー管理 |
| `tenant_admin` | 企業の管理者 | 自テナントのユーザー管理（manage-users） |
| `user` | 企業の一般社員 | ログイン・自データ閲覧 |

## 1ユーザー複数テナント所属

MVP（Phase 3）では1ユーザー1テナントのみ。  
複数テナント所属はPhase 4以降で検討する。

## 結果

- Keycloakの設定変更のみでテナントを追加できる（DB変更不要）
- JWTクレームの`tenant_id`で業務DBのRLSが動作する（既存実装を維持）
- Protocol Mapperは`realm-export.json`に含めることでポータブルに管理できる

## 参考

- [Keycloak Groups管理](https://www.keycloak.org/docs/latest/server_admin/#groups)
- [Keycloak Protocol Mappers](https://www.keycloak.org/docs/latest/server_admin/#_protocol-mappers)
