# 設計会議記録 — SaaS BtoBマルチテナント設計

**日時**: 2026-03-01  
**参加者**: PM, Architect, DB Specialist, Security Specialist, Senior Engineer  
**ドメインペルソナ**: 認証基盤 / IDaaS (OWASP Top 10, OAuth 2.0 / OIDC仕様, NIST SP 800-63)

---

## 背景

ADR-003で採用した「Realm per tenant」方式はオンプレ/顧客独立デプロイ向けの設計だった。
ユーザーの要件がSaaS BtoB（1インスタンス・複数企業テナント）に確定したため、設計を見直す。

## 要件

- SaaS BtoB: 1つのKeycloakインスタンス・1つのRealmで複数企業テナントを収容
- super_admin: テナント（企業）を登録・管理
- tenant_admin: 自テナントのユーザーのみ管理
- user: テナント内データのみアクセス
- データ分離: 業務DBでRLS（既存設計を維持）

## 設計決定

### テナント表現方式: Keycloak Groups + User Attribute

```
テナント「acme-corp」の構成:
  Keycloak Group:    /tenants/acme-corp
  User Attribute:    tenant_id = "acme-corp"
  JWT claim:         { "tenant_id": "acme-corp" }
  業務DB:            tenant_id = 'acme-corp'（RLS）
```

### 選択した理由

| 選択肢 | 判断 | 理由 |
|--------|------|------|
| Option A: Groupsのみ | 部分採用 | グループでテナント所属を管理するが、JWTへの単一値埋め込みにScriptMapperが必要（Keycloak 18+でデフォルト無効） |
| Option B: Organizations | 非採用 | Keycloak 26+の新機能でドキュメント・安定性が不十分 |
| Option C: User Attributeのみ | 部分採用 | JWTへの埋め込みは標準機能で確実に動作。グループで管理の可視性も確保 |
| **Groups + User Attribute** | **採用** | Groups=テナント所属の管理・可視化、Attribute=JWTへの確実な埋め込み |

### Keycloak設定変更

**Client Scope追加（Protocol Mapper）**:
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

**Group構造**:
```
/tenants/
  ├── acme-corp    (テスト用テナントA)
  └── globex-inc   (テスト用テナントB)
```

**テストユーザー更新**:
```
testuser@example.com:
  attributes.tenant_id = "acme-corp"
  groups: ["/tenants/acme-corp"]
  roles: [user]

admin@example.com:
  attributes.tenant_id = "acme-corp"
  groups: ["/tenants/acme-corp"]
  roles: [user, tenant_admin]

superadmin@example.com:
  attributes.tenant_id なし（全テナント管理）
  roles: [user, super_admin]
```

### Backend SDK設定変更

```env
# 変更前
TENANT_ID_SOURCE=iss

# 変更後
TENANT_ID_SOURCE=custom
TENANT_ID_CLAIM=tenant_id
```

### セキュリティ設計

- `tenant_id` User Attributeを変更できるのは **Keycloak Admin API経由のsuper_adminのみ**
- tenant_adminは`manage-users`権限を持つが、User Attributeの変更は上位権限（`manage-realm`）が必要
- フロントエンドのRBACは既存設計（Phase 3実装済み）を維持

## 議論のポイント

1. **テナント表現: Groups vs Organizations**
   - Engineerが指摘: Organizations（v26+）は機能が充実しているが安定性リスク
   - Security が指摘: Groups+Attributeの組み合わせが実績・安定性ともに最良
   - 決着: Groups（管理・可視化）+ Attribute（JWT埋め込み）のハイブリッド採用

2. **Protocol Mapperの実装方式**
   - Engineerが指摘: Group MembershipマッパーはリストでJWT埋め込み。単一値にはScriptMapperが必要だがデフォルト無効
   - 決着: User Attributeマッパー（標準機能）でシンプルに解決

3. **1ユーザー複数テナント所属**
   - PMが方針決定: MVP(Phase 3)では1ユーザー1テナントのみ。複数テナントはPhase 4以降

## ADR変更

- **ADR-003**: 改訂（Realm per tenant → Shared Realm + Groups + User Attribute）

## 次のアクション

- [ ] `realm-export.json` 更新（Client Scope + Protocol Mapper + Groups + テストユーザー属性）
- [ ] `auth-stack/.env.example` 更新（TENANT_ID_SOURCE=custom, TENANT_ID_CLAIM=tenant_id）
- [ ] `examples/fastapi-app/.env.example` 更新
- [ ] ADR-003 改訂
- [ ] `docs/_summary.md` 更新
