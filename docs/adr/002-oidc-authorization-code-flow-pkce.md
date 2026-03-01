# ADR-002: OIDC Authorization Code Flow + PKCEの採用

## ステータス

承認

## コンテキスト

SPAフロントエンド（React）からKeycloakに対してOIDC認証を行う際の認証フローを決定する必要がある。
OAuth 2.0 / OIDCには複数のフローが存在し、セキュリティ特性が異なる。

## 決定

**Authorization Code Flow + PKCE（Proof Key for Code Exchange）を採用する。**
Implicit FlowおよびResource Owner Password Credentials Grantは禁止する。

## 選択肢

### 選択肢A: Authorization Code Flow + PKCE（採用）
- **メリット**:
  - OAuth 2.1で推奨される最もセキュアなSPA向けフロー
  - アクセストークンがブラウザのURL履歴に残らない
  - PKCE（code_verifier / code_challenge）により認可コード横取り攻撃を防止
  - リフレッシュトークンによるサイレントトークン更新が可能
- **デメリット**:
  - Implicit Flowより実装がやや複雑（oidc-client-tsが吸収）

### 選択肢B: Implicit Flow
- **メリット**: 実装がシンプル
- **デメリット**:
  - OAuth 2.1で非推奨
  - アクセストークンがURLフラグメントに露出
  - リフレッシュトークンなし

### 選択肢C: Resource Owner Password Credentials Grant
- **メリット**: 独自ログインUIが使える
- **デメリット**:
  - OAuth 2.1で廃止予定
  - パスワードをフロントエンドが扱うセキュリティリスク
  - MFAとの統合が困難

## 結果

- OAuth 2.1推奨のセキュアな認証フローを実現
- PKCEにより、パブリッククライアント（SPA）でも安全に認可コードを交換可能
- oidc-client-tsがフローの複雑さを吸収し、開発者はHooksを呼ぶだけ
- Keycloakの認証画面を使用するため、パスワードがフロントエンドを経由しない

## 参考

- [OAuth 2.0 for Browser-Based Apps (RFC)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps)
- [PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)
