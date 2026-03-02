# ADR-011: ロールベースアクセス制御設計

## ステータス

Accepted (2026-03-01)

## コンテキスト

複数ロール（一般ユーザー・テナント管理者・スーパー管理者）を持つシステムで、フロントエンドのUI制御とバックエンドのAPI認可を一貫して行う方法を決定する必要があった。

## 決定

### ロール定義（Keycloakに一元管理）

| ロール | Keycloak設定 | 用途 |
|--------|-------------|------|
| `user` | Realm Role | 認証済み一般ユーザー |
| `tenant_admin` | Realm Role（Composite: manage-users） | テナント内ユーザー管理権限 |
| `super_admin` | Realm Role（Composite: realm-admin） | システム全体の管理権限 |

### フロントエンドでのロールチェック

JWTクレームの`realm_access.roles`配列を参照する。

```typescript
// AuthProviderで実装
const hasRole = (role: string): boolean => {
  return user?.profile?.realm_access?.roles?.includes(role) ?? false
}
```

**注意**: フロントエンドのロールチェックはUI表示制御のみに使用する。APIアクセス制御はバックエンドで再検証する。

### AuthGuardによるルート保護

```tsx
<AuthGuard requiredRoles={['tenant_admin', 'super_admin']}>
  <AdminUsers />
</AuthGuard>
```

### バックエンドでの権限検証

JWTクレームをミドルウェアで検証し、ロール不足は403を返す（フロントのロールチェックに依存しない）。

## 影響

- KeycloakのComposite Roleにより、`tenant_admin`ロールだけでrealmのユーザー管理権限（manage-users等）が自動的に付与される
- フロントエンドSDKに`hasRole()`と`AuthGuard.requiredRoles`を追加することで、アプリ開発者がシンプルに権限制御を実装できる
- JWTクレームに依存するため、ロール変更はトークン再発行まで反映されない（アクセストークン有効期限: 5分）
