# Review Log — feature/user-authentication

## メタデータ
- 日時: 2026-02-28 14:30:25
- 対象: feature/user-authentication
- レビュアー: Review Board（5人合議制）
- ラウンド: 1

## レビュー対象

```
変更ファイル:
  src/api/auth.ts          (+120, -0)
  src/models/user.ts       (+45, -10)
  tests/api/auth.test.ts   (+80, -0)

差分サマリー:
  - JWT認証の実装
  - ユーザーモデルにpassword_hashカラム追加
  - 認証エンドポイントのテスト追加
```

## Phase 1: 初見ラウンド

**PM**: 要件FR-003「ログイン機能」に対応しており、受入基準の「パスワード保護」が実装されている。ただし、セッション有効期限がPRDで定義した24時間になっているか確認が必要。

**Arch**: 認証ロジックがControllerに直書きされている。Service層への分離を推奨。将来的に認証方式を変更する場合に影響範囲が大きい。

**Eng**: 関数`authenticateUser`が50行を超えており、複数の責務を持っている。バリデーション・DB検索・トークン生成を分割すべき。エラーハンドリングは良好。

**Sec**: パスワードハッシュ化にbcryptを使用しており適切。ただし、認証失敗時のエラーメッセージが「ユーザーが存在しません」と「パスワードが違います」を区別しており、列挙攻撃のリスクがある。

**DB**: `users`テーブルに`password_hash`追加は問題なし。ただし、ログイン履歴を記録するテーブルがない。監査要件を満たすために`login_logs`テーブルを検討すべき。

## Phase 2: 議論

**Arch**: 「Engの指摘に同意。さらにControllerに直書きされているため、ユニットテストが困難。Service層に分離すれば、モックを使った効率的なテストが可能になる」

**Sec**: 「その修正をする場合、Service層での権限チェックも実装してほしい。Defense in Depthの原則として、Controller層だけでなくService層でも認証状態を検証すべき」

**Eng**: 「Secの指摘を踏まえると、AuthServiceクラスを作成し、authenticate/authorize/generateTokenの3メソッドに分割するのが良い」

**DB**: 「Secが指摘した監査ログ、login_logsテーブルを追加するならスキーマ設計を先にしたい。成功/失敗、IPアドレス、User-Agentを記録する仕様が必要」

**PM**: 「監査ログは重要だが、MVPスコープに含まれていない。フェーズ2での対応でも良いのでは。ただしスキーマ変更が発生するなら、今のうちにテーブル設計だけしておくのが賢明」

**Sec**: 「PMの言う通り、実装はフェーズ2でも良いが、テーブルだけ先に作っておけば後で楽。今回はINSERT処理を入れないだけで、スキーマとマイグレーションは追加を推奨」

## Phase 3: 判定

判定: REQUEST_CHANGES

[MUST FIX]
1. src/api/auth.ts:78 — 認証失敗時のエラーメッセージが列挙攻撃可能。「認証に失敗しました」に統一する
2. src/api/auth.ts:15-65 — authenticateUser関数をAuthServiceクラスに分離し、3メソッドに分割する

[SHOULD FIX]
1. docs/db/schema.sql — login_logsテーブルを追加（実装はフェーズ2でも可）
2. tests/api/auth.test.ts — 異常系テスト（無効なトークン、期限切れトークン）を追加

[CONSIDER]
1. src/api/auth.ts — レートリミット実装を将来的に検討（ブルートフォース対策）

[GOOD]
- bcryptによるパスワードハッシュ化が適切
- バリデーションロジックが明確に分離されている
- テストカバレッジが主要パスを網羅している

---

## 修正記録

修正日時: 2026-02-28 15:45:10
実施者: AI Agent

修正内容:
- [MUST FIX #1] ✅ エラーメッセージを統一（src/api/auth.ts:78）
- [MUST FIX #2] ✅ AuthServiceクラスを作成し、関数を分割（src/services/auth.service.ts）
- [SHOULD FIX #1] ✅ login_logsテーブルをスキーマに追加（docs/db/schema.sql）
- [SHOULD FIX #2] ✅ 異常系テスト4件を追加（tests/api/auth.test.ts）

未対応:
- [CONSIDER #1] ⏭️ レートリミットはフェーズ2で対応予定

---

## 再レビュー

再レビュー日時: 2026-02-28 16:00:35
ラウンド: 2

前回の指摘:
- [MUST FIX #1] ✅ 解決済み — エラーメッセージの統一を確認
- [MUST FIX #2] ✅ 解決済み — AuthServiceの分離と責務の明確化を確認
- [SHOULD FIX #1] ✅ 解決済み — login_logsスキーマを確認
- [SHOULD FIX #2] ✅ 解決済み — 異常系テストの追加を確認

新規指摘: なし

最終判定: APPROVE ✅

コメント: 全指摘事項が適切に解決されている。特にAuthServiceへの分離により、テスタビリティとメンテナンス性が大幅に向上した。`/push` でコミット可能。
