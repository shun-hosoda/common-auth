# ADR-005: Frontend OIDCライブラリの選定（oidc-client-ts）

## ステータス

承認

## コンテキスト

Frontend SDK（React + TypeScript）でKeycloakに対してOIDC Authorization Code Flow + PKCEを
実行するためのライブラリを選定する必要がある。

## 決定

**oidc-client-ts を採用し、React Hooksでラップして提供する。**

## 選択肢

### 選択肢A: oidc-client-ts（採用）
- **メリット**:
  - OIDC/OAuth 2.0の全フローに対応した成熟ライブラリ
  - TypeScriptネイティブ（型安全）
  - IdP非依存（Keycloak以外にも対応可能）
  - PKCE、サイレントリフレッシュ、自動トークン更新を標準サポート
  - 軽量（React等のUI依存なし）
- **デメリット**:
  - React統合は自前でHooksを実装する必要がある

### 選択肢B: keycloak-js（Keycloak公式SDKk）
- **メリット**: Keycloak専用で設定が最小、Keycloak機能をフル活用
- **デメリット**:
  - Keycloakにロックイン（将来のIdP変更時にSDK差替が必要）
  - React統合が公式にはない
  - バンドルサイズが大きい

### 選択肢C: react-oidc-context
- **メリット**: oidc-client-tsのReactラッパーとして完成度が高い
- **デメリット**: カスタマイズ性が制限される、SDK内部の制御が困難

## 結果

- oidc-client-tsにより、OIDC標準プロトコルに準拠したIdP非依存の認証フローを実現
- 自前のReact Hooks（`useAuth`, `useUser`）でプロジェクト固有のDXを提供
- 将来的にKeycloak以外のIdP（Cognito, Entra ID等）への移行時もSDK層の変更で吸収可能
- keycloak-jsへの依存を避けることで、ポータビリティ要件を満たす

## 参考

- [oidc-client-ts GitHub](https://github.com/authts/oidc-client-ts)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
