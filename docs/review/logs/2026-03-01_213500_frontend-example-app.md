# Review Log — Frontend Example App設計レビュー

## メタデータ
- 日時: 2026-03-01 21:35:00
- 対象: Frontend Example App (`examples/react-app/`) + 設計書 (`docs/design/frontend-example-app.md`)
- レビュアー: Review Board（5人合議制）
- ラウンド: 1

## レビュー対象

事後設計レビュー。実装済みのReact Example Appに対して設計書を作成し、コードと設計書の整合性を検証。

**変更ファイル一覧**:
- `docs/design/frontend-example-app.md` (新規)
- `examples/react-app/src/App.tsx`
- `examples/react-app/src/main.tsx`
- `examples/react-app/src/pages/Home.tsx`
- `examples/react-app/src/pages/Callback.tsx`
- `examples/react-app/src/pages/Dashboard.tsx`
- `examples/react-app/src/index.css`
- `examples/react-app/package.json`
- `examples/react-app/README.md`

## Phase 1: 初見ラウンド

**PM（プロダクトマネージャー）**:
設計書の目的とスコープは明確。ただし、エラーハンドリングの観点が弱い。Keycloakがダウンしている場合、ユーザーへの案内が不十分。SDKの使用例として、リトライロジックやフォールバック画面のパターンを示すべき。

**Arch（アーキテクト）**:
Callback.tsxで`UserManager`を独自に生成している点が問題。`AuthProvider`が既に`UserManager`を管理しているはずなのに、なぜ別のインスタンスを作るのか？これは設計の不整合で、トークンストレージの二重管理につながる可能性がある。

**Eng（シニアエンジニア）**:
Archの指摘に完全同意。さらに、`Home.tsx`の12-14行目で`navigate()`を条件分岐内で呼んでいるが、これはReactの`useEffect`外での副作用実行になる。レンダリング中に画面遷移を試みるのはアンチパターン。

**Sec（セキュリティスペシャリスト）**:
設計書のセキュリティセクション8は良いが、実装で「アクセストークンをクリップボードにコピー」機能がある。これは開発者向けデバッグ機能としても危険。トークンが意図せずSlackやメールに貼り付けられるリスクがある。本番環境では無効化すべき。

**DB（DBスペシャリスト）**:
このExample Appはフロントエンドのみなので、DB観点での指摘は限定的。ただし、設計書10.2で「マルチテナント対応」を拡張案として挙げているが、テナントIDの管理方法（クエリパラメータ vs サブドメイン vs クレーム）が未定義。

## Phase 2: 議論

**Arch**:
Engの指摘した`Home.tsx`の`navigate()`問題だが、実は`useEffect`で囲んでも根本解決にならない。認証済みユーザーがHomeにアクセスする状況自体を防ぐべき。React Routerの`loader`または`Navigate`コンポーネントで処理すべき。

**Eng**:
Archの提案に賛成。それと、Callbackコンポーネントの`UserManager`二重生成の問題は致命的。`AuthProvider`から`userManager`インスタンスを公開するか、`useAuth`に`handleCallback()`メソッドを追加するべき。

**Sec**:
Callbackの`UserManager`二重生成は、セキュリティ的にも問題。異なるインスタンスが異なるストレージキーを使う可能性があり、トークンリークのリスクがある。Engの提案する`useAuth().handleCallback()`が最も安全。

**PM**:
技術的な指摘は理解したが、ユーザー体験の観点で追加。設計書4の画面遷移図は詳細だが、「ログイン中にブラウザを閉じた場合」「トークン期限切れ時の挙動」が不明。これらはFAQセクションに追加すべき。

**DB**:
PMの指摘は妥当。加えて、設計書9.1で「本番ビルドバンドルサイズ~50KB」とあるが、`oidc-client-ts`だけで20KB以上ある。この見積もりは楽観的すぎる。実測値を記載すべき。

**Arch**:
DBの指摘を踏まえると、設計書の数値的主張は検証不足。TypeScriptの型チェックは通ったが、バンドルサイズ、ビルド時間の実測、Lighthouseスコアなどの非機能要件が未検証。

## Phase 3: 判定

**判定**: REQUEST_CHANGES

### [MUST FIX]

1. **`src/pages/Callback.tsx` — UserManager二重生成**
   - 問題: `AuthProvider`とは別に独自の`UserManager`インスタンスを生成している（L12-16）
   - リスク: トークンストレージの不整合、メモリリーク、セキュリティリスク
   - 対策: `useAuth()`に`handleCallback()`メソッドを追加し、`AuthProvider`管理下の`UserManager`を使用する

2. **`src/pages/Home.tsx` — レンダリング中の副作用実行**
   - 問題: 条件分岐内で直接`navigate()`を呼び出している（L12-14）
   - リスク: React警告、予期しない再レンダリング、無限ループの可能性
   - 対策: `useEffect`でラップするか、React Routerの`Navigate`コンポーネントを使用する

3. **`src/pages/Dashboard.tsx` — トークンコピー機能の本番環境リスク**
   - 問題: アクセストークンをクリップボードにコピーする機能（L10-16）
   - リスク: トークンが意図せず共有される、開発専用機能が本番に残る
   - 対策: 環境変数（`import.meta.env.DEV`）でデバッグ機能を制御する

### [SHOULD FIX]

1. **設計書 — Keycloakダウン時のエラーハンドリング未定義**
   - `AuthProvider`のエラー状態（`error`）がSDKで提供されているなら、その使用例を追加すべき
   - フォールバック画面のパターンを示す

2. **設計書9.1 — バンドルサイズの見積もり根拠不明**
   - 「~50KB」の根拠が示されていない
   - 実際に`npm run build`後の`dist/`サイズを測定して記載すべき

3. **設計書 — トークン期限切れ時の挙動未定義**
   - Silent Renewが失敗した場合のUXフローが不明
   - READMEのFAQセクションに追加すべき

### [CONSIDER]

1. **設計書10.2 — マルチテナント拡張のテナントID管理方法**
   - クエリパラメータ、サブドメイン、クレームのどれを採用するか、トレードオフを記載しておくと将来の参考になる

2. **非機能要件の実測**
   - Lighthouseスコア、バンドルサイズ、ビルド時間を一度測定し、設計書に追記すると説得力が増す

### [GOOD]

- 設計書の構成が非常に明確。目的・技術選定・画面遷移フローが体系的に整理されている
- OIDC+PKCEフローの図解が分かりやすく、開発者の理解を助ける
- TypeScriptの型チェックが通っており、基本的なコード品質は担保されている

---

## 修正記録

修正日時: 2026-03-01 21:40:00
実施者: AI Agent

### 修正内容

**[MUST FIX #1] ✅ UserManager二重生成の解消**
- `packages/frontend-sdk/src/types.ts`: `AuthContextValue`に`handleCallback()`を追加
- `packages/frontend-sdk/src/AuthProvider.tsx`: `handleCallback()`メソッドを実装
- `examples/react-app/src/pages/Callback.tsx`: `useAuth().handleCallback()`を使用するよう修正
- Frontend SDKをリビルド（v1.0.0）
- 単体テスト更新：`useAuth.test.tsx`に`handleCallback`のモックを追加
- **テスト結果**: 8 passed ✅

**[MUST FIX #2] ✅ レンダリング中の副作用実行の修正**
- `examples/react-app/src/pages/Home.tsx`: `useEffect`内で`navigate()`を実行するよう修正
- `useEffect`のインポートを追加

**[MUST FIX #3] ✅ トークンコピー機能の環境制御**
- `examples/react-app/src/pages/Dashboard.tsx`: `import.meta.env.DEV`で開発環境判定
- 本番ビルド時はトークンコピーボタンを非表示化
- `src/vite-env.d.ts`を追加してViteの型定義を有効化
- **型チェック**: 正常終了 ✅

**[SHOULD FIX #1] ✅ 設計書のエラーハンドリング追記**
- `docs/design/frontend-example-app.md`: 3.2 Callbackセクションにエラーハンドリングを追記
- 9.2 エラーハンドリングセクションを新設し、Keycloakダウン時、Silent Renew失敗時、トークン期限切れ時の挙動を明記

**[SHOULD FIX #2] ✅ バンドルサイズの実測値を記載**
- 設計書9.1を更新: Frontend SDK本体の実測値を記載（CJS: 6.5KB, ESM: 5.0KB）
- Example App全体は未測定として明記

**[SHOULD FIX #3] ✅ トークン期限切れ時の挙動を設計書に追記**
- 9.2 エラーハンドリングに含めて記載

**ドキュメント更新 ✅**
- `packages/frontend-sdk/README.md`: `handleCallback()`の使用例を追記、誤った`UserManager`直接生成例を修正
- `docs/design/frontend-example-app.md`: セキュリティセクション8に「UserManager一元管理」を追加

### 未対応

なし（MUST FIX、SHOULD FIXすべて対応完了）

### テスト実行結果

- Frontend SDK単体テスト: **8 passed** ✅
- React App型チェック: **正常終了** ✅
