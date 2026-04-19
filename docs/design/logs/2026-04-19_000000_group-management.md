# 設計会議記録 — グループ管理・権限設定 UI/API

## 参加者
PM, Architect, DB Specialist, Security Specialist, Senior Engineer  
ドメインペルソナ: 認証基盤 / IDaaS (OWASP Top 10, OAuth 2.0 / OIDC, NIST SP 800-63)

## 要件サマリー

- グループの追加/編集/削除画面が必要
- グループとユーザーを紐付けられるようにする
- グループまたはユーザーごとに権限設定ができるようにする
- `tenant_admin` ロールが操作する管理画面
- 既存の `docs/design/user-group-permission.md` と `docs/db/schema_groups_permissions.sql` の設計を活用する

---

## 設計決定

### API設計

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/admin/groups` | グループ一覧（`?page` `?search`） |
| POST | `/admin/groups` | グループ作成 |
| GET | `/admin/groups/{id}` | 詳細（`member_count`含む） |
| PUT | `/admin/groups/{id}` | 更新（名前・説明・親グループ） |
| DELETE | `/admin/groups/{id}` | 論理削除（`is_active=false`） |
| GET | `/admin/groups/{id}/members` | メンバー一覧 |
| POST | `/admin/groups/{id}/members` | メンバー追加（`user_ids[]` bulk対応） |
| DELETE | `/admin/groups/{id}/members/{user_id}` | メンバー削除 |
| GET | `/admin/groups/{id}/permissions` | 権限一覧（全定義+`granted`値） |
| PUT | `/admin/groups/{id}/permissions` | 権限一括更新 |
| GET | `/admin/users/{id}/groups` | ユーザーの所属グループ一覧 |
| POST | `/admin/users/{id}/groups` | グループ追加 |
| DELETE | `/admin/users/{id}/groups/{gid}` | グループ脱退 |
| GET | `/admin/users/{id}/permissions` | 実効権限一覧（継承済み含む） |
| PUT | `/admin/users/{id}/permissions` | 個別権限上書き |
| GET | `/admin/permissions` | 権限定義一覧（システム+テナントカスタム） |

#### グループ権限レスポンス例

```json
{
  "permissions": [
    { "id": "uuid", "resource": "users",   "action": "read",   "granted": true  },
    { "id": "uuid", "resource": "users",   "action": "write",  "granted": false },
    { "id": "uuid", "resource": "reports", "action": "read",   "granted": null  }
  ]
}
```

`granted` の意味:
- `true`  : 許可（`group_permissions` に `granted=true` レコードあり）
- `false` : 明示的拒否（`group_permissions` に `granted=false` レコードあり）
- `null`  : 未設定（レコードなし・デフォルト拒否）= PUT時にレコードをDELETE

### DB設計

変更なし（`schema_groups_permissions.sql` が既に完全定義済み）。

**グループ論理削除時の追加仕様:**
- `tenant_groups.is_active = false` に更新
- 子グループの `parent_group_id` を `NULL` に更新（ルートグループに昇格）
- `user_group_memberships` / `group_permissions` レコードは保持（監査用）
- 権限解決クエリの JOIN に `tenant_groups.is_active = true` フィルタを追加

### セキュリティ設計

| チェック項目 | 対応方法 |
|---|---|
| IDOR（他テナントのリソースへの不正アクセス） | サービス層で `tenant_id = current_user.tenant_id` 検証 + RLS |
| `tenant_admin` 権限ロック防止 | `tenant_admin` ロールユーザーへの権限変更は `super_admin` のみ許可 |
| `granted=null` vs `granted=false` の混同 | APIドキュメントと型定義で明確に区別・記載 |
| 権限一括更新のアトミック性 | DELETE + INSERT をトランザクション内で実行 |

### UIコンポーネント設計

```
/admin/groups
  └─ GroupList（テーブル + 検索 + ページネーション）
       ├─ GroupCreateModal（作成モーダル: 名前・説明・親グループ選択）
       └─ [行クリック] → /admin/groups/:id

/admin/groups/:id
  ├─ GroupHeader（名前・説明・親グループ表示・編集ボタン）
  └─ Tabs
       ├─ MembersTab
       │    ├─ UserTable（メンバー一覧: 名前・メール・追加日・削除ボタン）
       │    └─ AddMembersModal（ユーザー検索・複数選択追加）
       └─ PermissionsTab
            └─ PermissionMatrix（resource × action トグルグリッド）

/admin/users/:id（既存に追加）
  └─ Tabs の追加
       ├─ GroupsTab（所属グループ一覧 + グループ追加/脱退）
       └─ PermissionsTab（実効権限表示〔継承元表示付き〕+ 個別上書き設定）
```

#### 権限マトリックスUI状態

```
         read   write  delete  admin  export
users    [✅]   [✅]   [❌]    [❌]   [-]
reports  [✅]   [❌]   [❌]    [-]    [✅]
billing  [-]    [-]    [-]     [-]    [-]

[✅] = granted=true（緑・許可）
[❌] = granted=false（赤・明示的拒否）
[-]  = granted=null（グレー・未設定＝デフォルト拒否）
```

### 実装方針

- バックエンド: FastAPI に `/admin/groups` ルーターを追加（既存 `/admin/users` ルーターと同パターン）
- フロントエンド: React + 既存コンポーネント群を踏襲。`/admin/groups` ページ新規追加、`/admin/users/:id` にタブ追加
- 権限解決: `docs/design/user-group-permission.md` 記載の `WITH user_direct AS ...` クエリを流用
- キャッシュ: 権限解決結果は Redis TTL 5分でキャッシュ（高頻度アクセス時の対応）

---

## 議論のポイント

| 論点 | 議論の経緯 | 決着 |
|---|---|---|
| グループ削除時の子グループ処理 | Archが「孤児グループをどう扱うか」を提起。PM判断でシンプルにルート昇格 | 子グループの `parent_group_id = NULL` にして保持 |
| 権限更新は一括 vs 個別 | Engが「一括の方がUXもAPI設計もシンプル」と提案、全員合意 | `PUT + 配列` による一括更新 |
| `null` とレコードDELETEの扱い | Secが「null=解除なのか、デフォルト拒否なのかを明確化」と指摘 | `null` = レコードDELETE = デフォルト拒否に戻すとして統一 |
| Keycloakグループとの同期 | ArchがADR-003（ポータビリティ）を参照し非同期を提案 | 業務DBで独立管理。Keycloakグループとは同期しない |

---

## 起票すべきADR

- **ADR-012**: グループ権限をKeycloakと同期しない理由  
  （ADR-003の補足。業務DBで独立管理することでポータビリティを確保）

---

## 次のアクション

- [ ] `docs/api/openapi.yaml` に `/admin/groups` 系エンドポイントを追加
- [ ] ADR-012 を起票（任意: ADR-003の参照として）
- [ ] 実装計画会議（`/implement`）でTDD計画と実装順序を決定
