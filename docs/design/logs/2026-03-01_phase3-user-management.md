# 設計会議記録 — Phase 3: ユーザー管理・アクセス制御

**日時**: 2026-03-01  
**参加者**: PM, Architect, DB Specialist, Security Specialist, Senior Engineer  
**ドメインペルソナ**: 認証基盤 / IDaaS (OWASP Top 10, OAuth 2.0 / OIDC仕様, NIST SP 800-63)

---

## 要件サマリー（PRD FR-020〜FR-027）

| ID | 機能 | 優先度 |
|----|------|--------|
| FR-020 | ダッシュボード画面（認証済みのみ） | Must |
| FR-021 | ログイン画面（未認証のエントリーポイント） | Must |
| FR-022 | ログアウト → ログイン画面へリダイレクト | Must |
| FR-023 | クライアント管理（super_adminのみ） | Must |
| FR-024 | ユーザー管理画面（tenant_adminのみ表示） | Must |
| FR-025 | ユーザー登録・編集（tenant_admin操作） | Must |
| FR-026 | ロールベースUI制御（userはユーザー管理不可） | Must |
| FR-027 | Keycloak UIへの委譲（カスタムテーマ対応可） | Should |

---

## 設計決定

### ロール設計

| ロール | Keycloak対応 | 権限 |
|--------|-------------|------|
| `super_admin` | Realm-level `admin` | クライアント登録・全ユーザー管理・設定変更 |
| `tenant_admin` | `manage-users`（Client Role: `realm-management`） | 自Realm内のユーザー一覧・作成・編集・無効化 |
| `user` | デフォルト（認証済み） | ログイン・プロフィール・MFA・パスワードリセット |

### 画面遷移設計

```
/ (root)
 ├── 未ログイン → /login（Keycloakログイン画面へリダイレクト）
 └── ログイン済み → /dashboard

/dashboard [user以上]
 ├── user: プロフィール・ログアウト・MFA設定
 ├── tenant_admin: + ユーザー管理ボタン（/admin/users）
 └── super_admin: + クライアント管理ボタン（/admin/clients）

/admin/users [tenant_admin以上]
 └── Keycloak管理コンソールへディープリンク
     URL: {KEYCLOAK_URL}/admin/{realm}/console/#/users

/admin/clients [super_adminのみ]
 └── Keycloak管理コンソールへディープリンク
     URL: {KEYCLOAK_URL}/admin/master/console/#/common-auth/clients
```

### API設計

```
既存:
  GET  /auth/health     → ヘルスチェック
  GET  /auth/me         → 現在ユーザー情報

追加:
  GET  /auth/roles      → ユーザーのロール一覧
```

**Backend追加実装方針**:
- `/auth/me`のレスポンスにJWTの`realm_access.roles`を含める（すでに含まれる場合は確認）
- フロントはJWTクレームから直接ロールを取得可能のため、`/auth/roles`は補助的に必要に応じて追加

### Frontend SDK拡張

```typescript
// useAuth hookの拡張
interface AuthContextValue {
  // 既存
  user: User | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  
  // 追加
  hasRole: (role: string) => boolean;
  openUserManagement: () => void;  // Keycloak管理UIへのリンク生成
}

// AuthGuardの拡張
interface AuthGuardProps {
  children: ReactNode;
  requiredRoles?: string[];  // 追加: ロール要件
  fallback?: ReactNode;      // 追加: 権限不足時の表示
}
```

### ユーザー管理実装方針

**MVP（今回実装）**: Keycloak管理コンソールへのディープリンク委譲
- フロントエンドで`tenant_admin`ロールを確認
- 「ユーザー管理」ボタンをKeycloak管理コンソールのURL生成してリンク
- Keycloak側でテーマカスタマイズ（Freemarker / Keycloak React Admin UI）は将来対応

**将来（Phase 4）**: Backend Admin APIラッパー
- `GET/POST/PUT/DELETE /admin/users` → Keycloak Admin APIプロキシ
- カスタムUI（React管理画面）

### Keycloak設定変更（realm-export.json）

1. Realm Roleとして`super_admin`、`tenant_admin`を追加
2. テストユーザー（`admin@example.com`）に`tenant_admin`を付与
3. `super_admin`ユーザー（`superadmin@example.com`）を追加
4. Client Roleマッピング：`tenant_admin` → `manage-users`（realm-management）

### DB設計変更

追加不要。ロール情報はKeycloakが管理する。  
アプリ側DBには業務データのみ（RLSで既にtenant_id分離済み）。

---

## 議論のポイント

1. **ユーザー管理UI: カスタム実装 vs Keycloak委譲**
   - PM・Eng: MVP工数削減のためKeycloak委譲（Option B）を選択
   - Sec: 委譲でも`manage-users`権限の厳密な付与で対応可能

2. **フロントのロールチェック**
   - Sec: JWTクレーム（`realm_access.roles`）から取得するが、UI制御のみ。API側でも必ずバックエンド検証を行う
   - Eng: `hasRole()`をuseAuthに追加してフロント実装を簡略化

3. **super_adminのスコープ**
   - Arch: Keycloak adminは全権限のため、独立した管理者アカウントとして分離
   - PM: MVPでは`superadmin@example.com`をテストユーザーとして準備するだけでOK

---

## 起票すべきADR

- **ADR-010**: ユーザー管理UI実装方針（Keycloak委譲 vs カスタム実装）
- **ADR-011**: ロールベースアクセス制御設計（Keycloakロール + JWTクレーム）

---

## 次のアクション

- [ ] `realm-export.json` にロール追加（super_admin, tenant_admin, テストユーザー）
- [ ] Frontend SDK: `hasRole()` を `useAuth` に追加
- [ ] Frontend SDK: `AuthGuard` に `requiredRoles` を追加
- [ ] React example app: Dashboard にロールベース表示制御を追加
- [ ] React example app: `/admin/users` 画面（Keycloak リンク付き）を追加
- [ ] ADR-010, ADR-011 を起票
- [ ] 設計レビュー（/review --design）
