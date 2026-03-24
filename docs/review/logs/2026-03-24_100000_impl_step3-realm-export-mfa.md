# レビューログ — Step 3: Keycloak realm-export.json MFA設定

**日時**: 2026-03-24
**ゲート**: Gate 2（実装完了）
**フェーズ**: impl
**対象ファイル**: `auth-stack/keycloak/realm-export.json`
**差分**: +117行 / -7行

---

## 差分サマリ

| 変更区分 | 内容 |
|---------|------|
| `serviceAccountClientRoles` 削除 | `admin-api-client` クライアントから削除（KC 24非対応） |
| グループ属性追加 | `acme-corp`, `globex-inc` に `mfa_enabled: ["false"]`, `mfa_method: ["totp"]` |
| SA ユーザー追加 | `users` 配列に `service-account-admin-api-client` エントリ（`realm-admin` ロール付き） |
| 認証フロー追加（4件） | `unified-mfa-browser` (top), `forms`, `mfa-gate`, `totp-subflow` |
| authenticatorConfig（2件） | `mfa-gate-condition`, `mfa-totp-condition` |
| browserFlow 変更 | `"unified-mfa-browser"` に切替 |
| Email OTP 削除 | 設計書の5フロー/4コンフィグから除去（KC 24.0.5 に `auth-email-otp-form` なし） |

---

## 検証結果（実装時に実施済み）

- ✅ Realm import成功（`Realm 'common-auth' imported`）
- ✅ P1: roles mapper `id.token.claim=true`
- ✅ P2: SMTP `host=mailhog port=1025`
- ✅ `browserFlow = unified-mfa-browser`
- ✅ グループ属性: 両テナント `mfa_enabled=false`, `mfa_method=totp`
- ✅ SA realm-admin ロール確認
- ✅ SA トークン取得: OK (length=1537)
- ✅ 通常ユーザーログイン: OK
- ✅ Backend テスト: 97 passed, 0 failed

---

## 指摘事項

| ID | 重要度 | 指摘者 | 内容 | ステータス |
|----|--------|--------|------|-----------|
| M1 | MUST FIX | Security / PM | 設計書 (login-flow.md, tenant-policy.md) の Email OTP 関連記述を TOTP のみに更新。Email OTP は「KC 26+ 対応予定」と明記 | ✅ /fix で対応済 |
| C1 | CONSIDER | Engineer | `otpPolicyAlgorithm: "HmacSHA1"` → HmacSHA256 に変更済み | ✅ /fix で対応済 |

---

## 投票

| 専門家 | 判定 | 備考 |
|--------|------|------|
| Product Manager | APPROVE with conditions | M1 |
| Architect | APPROVE | — |
| Senior Engineer | APPROVE | C1 は将来課題 |
| Security Specialist | APPROVE with conditions | M1 |
| DB Specialist | APPROVE | — |

**結論**: 条件付き APPROVE（M1 対応必須）

---

## /re-review (2026-03-24)

### 前回指摘の解消確認

| ID | ステータス | 確認内容 |
|----|-----------|---------|
| M1 | ✅ 解消 | login-flow.md: 9箇所更新（フロー構造・authenticatorConfig・ログインフロー図・§4〜§9）。tenant-policy.md: 7箇所更新（API仕様・更新処理・Frontend UI・テスト計画）。全て「KC 26+ 対応予定」で一貫した記述。 |
| C1 | ✅ 解消 | realm-export.json `otpPolicyAlgorithm` → `HmacSHA256`。Keycloak Admin API で確認済み。主要認証アプリ互換性問題なし。 |

### 回帰・副作用チェック

- ✅ realm-export.json JSON valid（Keycloak import成功）
- ✅ P1/P2/browserFlow/グループ属性/SA — 影響なし
- ✅ 設計書間の整合性（login-flow.md ↔ tenant-policy.md）
- ✅ 設計書 ↔ realm-export.json の整合性

### 投票

| 専門家 | 判定 |
|--------|------|
| Product Manager | APPROVE |
| Architect | APPROVE |
| Senior Engineer | APPROVE |
| Security Specialist | APPROVE |
| DB Specialist | APPROVE |

**結論**: **全員一致 APPROVE**
