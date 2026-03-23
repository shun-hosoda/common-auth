# 設計レビュー — MFAテナントポリシー管理

**日時**: 2026-03-20
**初回判定**: CONDITIONAL APPROVE → **再レビュー: APPROVE ✅**
**対象ファイル**:
- `docs/design/auth/mfa/tenant-policy.md`
- `docs/design/auth/mfa/login-flow.md`
- `docs/design/auth/mfa/account-settings.md`
- `docs/ui/flows.md`

**PRD参照**: Phase 3.5 (FR-030〜FR-037)

---

## MUST FIX（4件）

### M-ARCH-1: `/api/auth/mfa-status` のルーターパス二重化

**対象**: account-settings.md §5

auth router は `prefix="/auth"` で登録されている（setup.py L66）。
設計書のコード例 `@auth_router.get("/auth/mfa-status")` では実URLが `/auth/auth/mfa-status` になる。

**修正**: `@router.get("/mfa-status")` に修正。設計書のURL表記は `/api/auth/mfa-status`（Vite proxy 経由）で統一。

### M-ARCH-2: auth router から KeycloakAdminClient を使う依存設計の欠落

**対象**: account-settings.md §5

`GET /api/auth/mfa-status` の実装方針で「Keycloak Admin API でクレデンシャル一覧を取得」とあるが、
auth router には `KeycloakAdminClient` へのアクセスが存在しない。

**修正**: auth router 用の `_get_kc_admin` ヘルパー追加、または `setup.py` で `app.state` に
`KeycloakAdminClient` を初期登録して全 router から参照する設計を明記。

### M-ENG-1: 更新処理フローの Step 5/7 実行順序・条件の曖昧さ

**対象**: tenant-policy.md §2

Step 5（MFA有効化）と Step 7（方式変更検知）の実行条件が重複・曖昧。
既にMFA有効の状態で方式だけ変更した場合にどちらが実行されるか不明確。

**修正**: フローを以下に再構成：
1. 権限チェック
2. 現在のグループ属性を取得（旧値保持）
3. グループ属性を更新
4. 方式変更の有無を判定 → 変更あればOTPクレデンシャル一括リセット
5. 最終状態に基づきユーザー属性・Required Action を設定
6. レスポンス返却

### M-SEC-1: MFA再有効化時の mfa_method ミラーリング不整合

**対象**: tenant-policy.md §2

Step 6 で「mfa_method は保持」とあるが、無効化中にグループ属性の mfa_method が
変更された場合、再有効化時にユーザー属性が旧値のまま残る。

**修正**: Step 5a で「mfa_enabled, mfa_method を**グループ属性の値で**上書き」と明記。

---

## SHOULD FIX（6件）

### S-PM-1: PRDにアカウント設定のユーザーストーリー追加

account-settings.md の機能（MFAステータスカード、mfa-status API）にPRDの
ユーザーストーリーが存在しない。US-6 を追加推奨。

### S-ARCH-1: authenticationFlows JSON定義を1箇所にまとめる

tenant-policy.md と login-flow.md が互いに参照し合い、完全なJSON定義が存在しない。
tenant-policy.md に完全な `authenticationFlows` JSON を記載すべき。

### S-ENG-1: find_group_by_name のグループ属性返却確認

Keycloak Groups API はバージョンにより `attributes` を含まない場合がある。
追加メソッド `get_group(group_id)` の利用箇所をフロー内に明示すべき。

### S-ENG-2: テスト計画の追加

成果物一覧にテスト追加が含まれるが、テストケース設計がない。
正常系・異常系・境界値のテストケース一覧を追加すべき。

### S-SEC-1: super_admin のMFAポリシー適用ルール明記

super_admin が複数テナントに属する場合のMFAポリシー適用ルールが不明確。
プライマリテナント（tenant_id 属性のテナント）ルール等を明記すべき。

### S-SEC-2: Email OTP ブルートフォース保護の明記

コード入力の試行回数制限について、Keycloakデフォルト設定の適用有無を確認・明記すべき。

---

## INFO（2件）

| ID | 内容 |
|----|------|
| I-PM-1 | Phase 4+先送り項目が明確に整理されている |
| I-DB-1 | realm-export.json 初期値は実装時対応で可 |

---

## 再レビュー（/re-review）

**日時**: 2026-03-20
**判定**: **APPROVE ✅**

### MUST FIX 解消確認

| ID | 指摘 | 修正内容 | 判定 |
|----|------|---------|------|
| M-ARCH-1 | `/api/auth/mfa-status` パス二重化 | `@router.get("/mfa-status")` に修正 + prefix注意書き追加 | ✅ 解消 |
| M-ARCH-2 | auth router の KC依存欠落 | `setup.py` での `app.state` 一元登録 + 共通ヘルパー設計を追記 | ✅ 解消 |
| M-ENG-1 | 更新フロー Step 5/7 曖昧 | 8ステップに再構成（旧値保持→方式変更判定→最終状態設定） | ✅ 解消 |
| M-SEC-1 | 再有効化時 mfa_method 不整合 | Step 6b で「グループ属性の値で上書き」を明記 | ✅ 解消 |

### SHOULD FIX 解消確認

| ID | 修正内容 | 判定 |
|----|---------|------|
| S-PM-1 | PRD に US-6 追加 | ✅ 解消 |
| S-ARCH-1 | login-flow.md §8 に authenticationFlows 完全JSON追加（5フロー+4設定） | ✅ 解消 |
| S-ENG-1 | 更新フロー Step 2 に `find_group_by_name` → `get_group(id)` 2段階取得を明記 | ✅ 解消 |
| S-ENG-2 | tenant-policy.md §6 にテスト計画15件追加 | ✅ 解消 |
| S-SEC-1 | login-flow.md §7 でプライマリテナントルールを明記 | ✅ 解消 |
| S-SEC-2 | login-flow.md §4 にブルートフォース保護セクション追加 | ✅ 解消 |

### 回帰・副作用チェック

| チェック項目 | 結果 |
|---|---|
| 3文書間の相互参照が正しいか | ✅ login-flow.md §8 → tenant-policy.md 参照が維持 + JSON定義が追加で自己完結化 |
| 更新フロー再構成で抜け落ちがないか | ✅ 旧フローの全処理（有効化・無効化・方式変更）が新8ステップに包含 |
| `_get_kc_admin` 共通化が admin router 既存動作に影響しないか | ✅ 同一パターン（`app.state` 参照）への移行、破壊的変更なし |
| PRD US-6 追加が他ストーリーと矛盾しないか | ✅ US-4（ログイン時MFA）と補完関係 |
| authenticationFlows JSON の構造が §1 フロー図と一致するか | ✅ 5フロー・4 authenticatorConfig が §1 と完全対応 |

### 別観点レビュー

**運用性**: 部分失敗時に失敗ユーザーIDリストを返す設計が追加され、運用者が問題特定しやすくなった。冪等性によるリトライ設計も適切。

**一貫性**: 3文書全てで更新日が `2026-03-20` で統一。成果物一覧の auth router 関連が account-settings.md のみに記載されている点は、実装時に注意すべきだが設計上は問題なし。
