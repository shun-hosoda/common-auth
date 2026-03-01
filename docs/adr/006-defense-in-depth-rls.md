# ADR-006: RLSによるDefense in Depthの採用

## ステータス

承認

## コンテキスト

マルチテナント構成において、テナント間のデータ分離は最重要のセキュリティ要件である。
Backend SDKのミドルウェアで`tenant_id`フィルタリングを行うが、以下のリスクが存在する:

- ミドルウェア実装のバグ
- ORMバイパス（生SQL直接実行）
- 将来の開発者による意図しないデータアクセス

単一の防御層に依存すると、その層の突破で全データが漏洩する。

## 決定

**PostgreSQL Row-Level Security (RLS) を有効化し、Defense in Depth（多層防御）を実現する。**

### 防御層の構成

```
┌───────────────────────────────────────┐
│  Layer 1: Backend Middleware          │
│  - JWT から tenant_id を抽出          │
│  - ORM/SQL に tenant_id フィルタ付与  │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│  Layer 2: Row-Level Security (RLS)    │
│  - DB層で tenant_id を強制検証       │
│  - app.current_tenant_id と照合       │
└───────────────────────────────────────┘
```

### 実装方針

1. **デフォルト: RLS有効**
   - `user_profiles`テーブルで`ENABLE ROW LEVEL SECURITY`
   - ポリシー: `tenant_id = current_setting('app.current_tenant_id')::UUID`

2. **Backend SDKの責務**
   - リクエスト開始時に`SET LOCAL app.current_tenant_id = '<tenant_id>'`を実行
   - トランザクション終了時に自動クリア（`LOCAL`スコープ）

3. **単一テナント構成での無効化**
   - RLSが不要な場合は`ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY`で無効化可能
   - ただし、無効化時のリスクを理解した上で実施

### RLS無効化時のリスク

| リスクシナリオ | 影響 | 対策 |
|---|---|---|
| ミドルウェアのバグ | テナント間データ漏洩 | 自動テストで検証 |
| 生SQL直接実行 | フィルタバイパス | コードレビューで監視 |
| 将来の機能追加 | 意図しないアクセス | ADRで警告を残す |

## 選択肢

### 選択肢A: RLSデフォルト有効（採用）
- **メリット**: DBレベルで強制的に分離、ミドルウェアバグの影響を緩和
- **デメリット**: `SET app.current_tenant_id`の設定が必須、わずかな性能オーバーヘッド

### 選択肢B: ミドルウェアのみ（RLS無効）
- **メリット**: 実装がシンプル、性能オーバーヘッドなし
- **デメリット**: 単一障害点、バグ発生時の被害が大きい

### 選択肢C: スキーマ分離（Realm = DB Schema）
- **メリット**: PostgreSQL名前空間レベルで完全分離
- **デメリット**: テナント数の上限、管理複雑度の増加

## 結果

- ミドルウェアのバグや将来の実装ミスによるデータ漏洩リスクを大幅に削減
- RLS設定忘れによる事故を防ぐため、`schema.sql`でデフォルト有効化
- 単一テナント構成では顧客判断で無効化可能（ドキュメントでリスク明記）
- テナント分離の自動テストを必須化（Backend SDK開発時）

### テナント分離テスト戦略

```python
def test_tenant_isolation():
    """テナントAのユーザーがテナントBのデータにアクセスできないこと"""
    # Arrange
    tenant_a_token = create_token(tenant_id="tenant-a", user_id="user-1")
    tenant_b_profile = create_user_profile(tenant_id="tenant-b", user_id="user-2")
    
    # Act
    response = client.get(
        f"/api/users/{tenant_b_profile.id}",
        headers={"Authorization": f"Bearer {tenant_a_token}"}
    )
    
    # Assert
    assert response.status_code == 404  # テナントBのデータは存在しないように見える
```

## 参考

- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP: Insecure Direct Object Reference (IDOR)](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References)
