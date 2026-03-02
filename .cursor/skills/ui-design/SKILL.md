---
name: ui-design
description: UIの設計・実装を行う。画面設計、コンポーネント設計、デザインシステム、レスポンシブ対応、アクセシビリティを扱う。新規画面の作成、既存UIの刷新、コンポーネント追加、スタイル改善、デザイントークン定義など、あらゆるUI作業に使用する。
---

# UI Design Skill

## UI設計ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/ui/design-system.md](../../../../docs/ui/design-system.md) | デザイントークン・コンポーネント一覧（Single Source of Truth） |
| [docs/ui/flows.md](../../../../docs/ui/flows.md) | 画面遷移フロー・認可マトリックス |
| [docs/ui/screens/](../../../../docs/ui/screens/) | 各画面の仕様書（ワイヤーフレーム・状態・SP対応） |

**実装前に必ず上記を確認・更新すること。**

---

## 進め方（Design First）

UIタスクを受けたら必ず次の順序で実行する。**設計書なしに実装を開始してはならない。**

1. **設計書確認** — `docs/ui/` の該当ファイルを読む。なければ作成する
2. **設計会議** — 5人専門家が実際に意見を述べて議論する（工程の列挙だけは不可）
3. **設計書更新** — 決定内容を `docs/ui/screens/<screen>.md` に記録する
4. **実装** — デザイントークン → コンポーネント → 画面の順
5. **レビュー** — チェックリストで品質確認

---

## 設計会議（5人専門家）

UIタスクを受けたら、**工程を示すだけでなく** 必ず5人の専門家が実際に意見を述べて議論し、設計上のトレードオフや判断理由を明示する。

| 役割 | 担当観点 |
|------|----------|
| UXデザイナー | 情報設計・ユーザーフロー・導線・インタラクション |
| UIデザイナー | レイアウト・タイポグラフィ・カラー・視覚階層 |
| フロントエンドエンジニア | コンポーネント分割・状態管理・パフォーマンス |
| アクセシビリティ専門家 | WCAG・キーボード操作・スクリーンリーダー・SP対応 |
| プロダクトマネージャー | 要件整合・MVP絞り込み・ユーザーゴール |

**議論の進め方**:
1. 各専門家が自分の観点から課題・提案・懸念を述べる
2. 意見が対立する場合はトレードオフを明示して合意を得る
3. 設計決定事項とその理由を記録する

---

## 設計原則

### 関心の分離
- ビジネスロジックと表示ロジックを分離する
- データ取得はhooks/services層、描画はコンポーネント層に置く
- コンポーネントはpropsで動作を制御し、副作用を持たせない

### デザイントークン
色・サイズ・スペーシングはすべてCSS変数またはトークンオブジェクトで管理する。
ハードコードしない。

```css
/* カラー */
--color-primary: #2563eb;
--color-success: #16a34a;
--color-warning: #d97706;
--color-danger:  #dc2626;
--color-bg:      #f8fafc;
--color-surface: #ffffff;
--color-border:  #e2e8f0;
--color-text:    #1e293b;
--color-text-muted: #64748b;

/* スペーシング: 4px基準 */
--space-1: 4px;  --space-2: 8px;  --space-3: 12px;
--space-4: 16px; --space-6: 24px; --space-8: 32px;

/* 角丸 */
--radius-sm: 4px; --radius-md: 8px;
--radius-lg: 12px; --radius-full: 9999px;

/* シャドウ */
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
```

### コンポーネント設計
- 単一責任：1コンポーネント1役割
- 汎用部品（Button, Card, Badge 等）を先に定義してから画面を組む
- `variant` / `size` propsでバリエーションを持たせる

### レイアウト構造
```
AppShell
├── TopBar / Header
├── [Sidebar / SideNav]      ← 必要な場合のみ
└── Main
    ├── PageHeader            ← タイトル + アクションボタン
    └── ContentArea           ← Cards / Table / Form
```

---

## 汎用コンポーネント一覧

| コンポーネント | 用途 | 主要props |
|---|---|---|
| `Button` | 操作ボタン | `variant(primary/secondary/danger/ghost)`, `size(sm/md/lg)`, `icon` |
| `Card` | コンテンツブロック | `padding`, `shadow` |
| `Badge` | ステータス・ラベル | `color`, `label` |
| `Avatar` | ユーザーアイコン | `initials`, `size`, `src` |
| `Alert` | 通知メッセージ | `type(success/warning/error/info)`, `message` |
| `Modal` | ダイアログ | `isOpen`, `onClose`, `title` |
| `Table` | データ一覧 | `columns`, `rows`, `onRowClick` |
| `Form` | 入力フォーム | `onSubmit`, `fields` |
| `Spinner` | ローディング | `size` |
| `EmptyState` | データなし | `message`, `action` |

詳細な実装例: [components.md](components.md)

---

## 実装チェックリスト

### 機能
- [ ] ローディング状態を表示する（Spinner / skeleton）
- [ ] エラー状態を表示する（Alert / inline error）
- [ ] 空データ状態を表示する（EmptyState）
- [ ] 操作の成功フィードバックを返す（Toast / Alert）

### アクセシビリティ
- [ ] セマンティックHTML（`<header>`, `<main>`, `<nav>`, `<section>`, `<form>`）
- [ ] インタラクティブ要素に `aria-label` または可視テキスト
- [ ] フォーム要素に `<label>` と `htmlFor`
- [ ] キーボードでTab移動できる（`:focus-visible` スタイルあり）
- [ ] エラーメッセージを `role="alert"` で通知

### SP（スマートフォン）対応【必須】
- [ ] 768px以下でモバイルレイアウトに切り替わる（必須）
- [ ] タップターゲット 44×44px以上（必須）
- [ ] 横スクロールが発生しない（必須）
- [ ] フォント最小 14px以上（必須）
- [ ] モバイル時はサイドバーをハンバーガーメニューまたはボトムナビに変更
- [ ] テーブルはモバイルでカード形式にフォールバック

### CSS品質
- [ ] `!important` 不使用
- [ ] ハードコードの色・サイズなし（トークン使用）
- [ ] `prefers-reduced-motion` でアニメーション抑制

---

## CSS注意点

```css
/* アニメーション抑制 */
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}

/* フォーカス可視化 */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* レスポンシブ例 */
@media (max-width: 768px) {
  .page-layout { flex-direction: column; }
  .sidebar { display: none; }
}
```

---

## 参考

- トークン全量: [design-tokens.md](design-tokens.md)
- コンポーネント実装例: [components.md](components.md)
