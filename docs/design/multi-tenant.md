# マルチテナント設計書 — SaaS BtoB（Shared Realm + Groups）

## 1. 概要

SaaS BtoB（1インスタンス・複数企業テナント）向けのマルチテナント設計。
1つのKeycloakインスタンス・1つのRealmで複数企業テナントを収容する。

### 背景

[ADR-003](../adr/003-multi-tenant-realm-isolation.md) で当初採用した「Realm per tenant」方式は
オンプレ/顧客独立デプロイ向けの設計だった。
SaaS BtoB要件の確定に伴い、Shared Realm + Groups方式に改訂。

---

## 2. テナント表現方式: Keycloak Groups + User Attribute

```
テナント「acme-corp」の構成:
  Keycloak Group:    /tenants/acme-corp
  Group Attribute:   tenant_id = "acme-corp"
  User Attribute:    tenant_id = "acme-corp"
  JWT claim:         { "tenant_id": "acme-corp" }
  業務DB:            tenant_id = 'acme-corp'（RLS）
```

### 方式選定

| 選択肢 | 判断 | 理由 |
|--------|------|------|
| Groupsのみ | 部分採用 | JWTへの単一値埋め込みにScriptMapper必要（デフォルト無効） |
| Organizations (v26+) | 非採用 | ドキュメント・安定性が不十分 |
| User Attributeのみ | 部分採用 | JWTへの埋め込みは標準機能で確実に動作 |
| **Groups + User Attribute** | **採用** | Groups=管理・可視化、Attribute=JWTへの確実な埋め込み |

---

## 3. Keycloak設定

### Client Scope（Protocol Mapper）

```json
{
  "name": "tenant",
  "protocol": "openid-connect",
  "attributes": { "include.in.token.scope": "true" },
  "protocolMappers": [{
    "name": "tenant-id-mapper",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usermodel-attribute-mapper",
    "config": {
      "user.attribute": "tenant_id",
      "claim.name": "tenant_id",
      "jsonType.label": "String",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "userinfo.token.claim": "true"
    }
  }]
}
```

### Group構造

```
/tenants/
  ├── acme-corp     (テスト用テナントA)
  └── globex-inc    (テスト用テナントB)
```

### 業務DBテナント

業務DB（app-db）には3テナントがシードされる:

| realm_name | display_name | 用途 |
|------------|-------------|------|
| `common-auth` | Common Auth Test Tenant | SDKテスト用 |
| `acme-corp` | Acme Corp | テストテナントA |
| `globex-inc` | Globex Inc | テストテナントB |

### グループ属性

```json
{
  "name": "acme-corp",
  "path": "/tenants/acme-corp",
  "attributes": {
    "tenant_id": ["acme-corp"],
    "mfa_enabled": ["false"],
    "mfa_method": ["totp"]
  }
}
```

> `mfa_enabled` / `mfa_method` は [Phase 3.5 MFA設計](auth/mfa/tenant-policy.md) で追加。

---

## 4. テストユーザー

| ユーザー | tenant_id | グループ | ロール |
|---------|-----------|---------|--------|
| `testuser_acme-corp@example.com` | acme-corp | /tenants/acme-corp | user |
| `admin_acme-corp@example.com` | acme-corp | /tenants/acme-corp | user, tenant_admin |
| `testuser_globex-inc@example.com` | globex-inc | /tenants/globex-inc | user |
| `admin_globex-inc@example.com` | globex-inc | /tenants/globex-inc | user, tenant_admin |

> `super_admin` ロールはRealmレベルで定義済みだが、現在のテストデータでは割り当てられているユーザーはいない。運用時にKeycloak Adminコンソールから手動で付与する。
> MVPでは1ユーザー1テナントのみ。複数テナント所属はPhase 4以降で検討。

---

## 5. Backend SDK設定

```env
# 変更前（Realm per tenant）
TENANT_ID_SOURCE=iss

# 変更後（Shared Realm + Groups）
TENANT_ID_SOURCE=custom
TENANT_ID_CLAIM=tenant_id
```

### テナント境界の強制

- Backend Admin APIで `tenant_id` クレームによるフィルタリング必須
- `tenant_admin` は自テナントのユーザーのみ操作可能
- `super_admin` は全テナントにアクセス可能
- `tenant_id` User Attribute の変更は Keycloak Admin API 経由の super_admin のみ

---

## 6. セキュリティ設計

| 脅威 | 対策 |
|------|------|
| テナント越境アクセス | JWT `tenant_id` クレームでバックエンド強制フィルタ |
| tenant_id改ざん | User Attribute変更はsuper_admin権限必須 |
| RLS回避 | 業務DBでRLSポリシー適用（[ADR-006](../adr/006-defense-in-depth-rls.md)） |
| JWT claim偽造 | RS256署名検証 + JWKS公開鍵キャッシュ |

---

## 7. 関連ADR

| ADR | 決定 |
|-----|------|
| [ADR-003](../adr/003-multi-tenant-realm-isolation.md) | Shared Realm + Groups（改訂済み） |
| [ADR-006](../adr/006-defense-in-depth-rls.md) | 多層防御RLS |

---

*元ログ: [設計会議記録 — SaaS BtoBマルチテナント設計](logs/2026-03-01_saas-multitenant.md)*
