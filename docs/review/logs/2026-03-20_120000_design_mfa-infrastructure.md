# レビュー記録 #001 — Keycloak MFA 設計レビュー

## レビュー対象
- `docs/prd/prd.md`
- `docs/design/logs/design-001-mfa.md`
- `docs/adr/adr-001-keycloak-mfa.md`
- `docs/implementation/logs/impl-001-mfa.md`

## 指摘一覧と対応

| # | 優先度 | 指摘者 | 内容 | 対応 |
|---|--------|--------|------|------|
| 1 | 🚨 MUST | セキュリティ | `.env` シークレット管理ルールの明記 | ✅ 設計書§4・§6・ADR に追記 |
| 2 | ⚠️ SHOULD | アーキテクト | realm-export 分離方針をADRに明記 | ✅ ADR に採択理由・トレードオフを追記 |
| 3 | ⚠️ SHOULD | PM | メール再送ボタンの実現手段 | ✅ 設計書§5 に追記 |
| 4 | ⚠️ SHOULD | セキュリティ | OTPリセット操作の認可要件 | ✅ 設計書§7 に Realm Admin 限定を明記 |
| 5 | ⚠️ SHOULD | DBスペシャリスト | PostgreSQL healthcheck の明記 | ✅ 設計書§3 に追記 |
| 6 | ⚠️ SHOULD | シニアエンジニア | Phase 2（Cookie）のPhase 1非干渉性 | ✅ 設計書§8 に追記 |

## 再レビュー結果（Step 1実装修正後）

### 判定
**❌ CHANGES REQUESTED**

### 解消確認
- ✅ `.env` のgit管理除外ルール
- ✅ `docker-compose.yml` の `restart: unless-stopped`
- ✅ PostgreSQL DB名の環境変数化
- ✅ 開発環境向けの注意事項追記

### 未解消 / 追加確認（MUST/SHOULD）
1. **MUST**: `auth-email-otp-form` のAuthenticator ID実在確認  
   - Keycloak v24環境で `kcadm` もしくは管理UIから利用可能Provider IDを確認し、`realm-export.json` と一致させること。
2. **SHOULD**: SMTP設定源の一本化  
   - `realm-export.json` の `smtpServer` を正とするか、起動時設定を正とするかを統一し、二重管理を解消すること。

### 次アクション
`/fix` で上記2点を修正後、`/re-review` を再実行する。

## /fix 追補（SMTP一本化 + Provider ID検証）

- ✅ SMTP設定源を `docker-compose.yml` に一本化（`realm-export.json` の `smtpServer` 削除）
- ✅ Email OTP Provider ID は `auth-email-otp-form` に固定し、実装ログに実在確認手順を追加

## 再レビュー結果（Step 2: TOTPフロー修正版）

### 判定
**✅ APPROVED**

### 解消確認
- ✅ `custom-totp-cookie` の `auth-cookie` は `DISABLED` に統一（Phase 2方針と整合）
- ✅ `docker-compose-totp.yml` に「TOTPはmailhog不要」を明記
- ✅ Step 1/Step 2 compose重複は「顧客別明確化優先」の運用方針を明記
- ✅ 2回目ログイン検証時の「プライベートウィンドウ使用」を手順化
- ✅ 誤コード3回でロック確認手順を追加

### request1.txt 整合性
- ✅ §2 初回QR設定強制（Required Action: Configure OTP）
- ✅ §2 2回目以降コード入力のみ
- ✅ §3 リカバリー運用（管理者OTPリセット手順）

### ステータス
Step 2（TOTP）実装はレビュー完了。次工程へ進行可能。
