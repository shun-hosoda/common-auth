# UI デザインシステム

**Single Source of Truth** — このファイルが全画面のUI設計の基準となる。
実装時は必ずここを参照し、ここに記載のないトークン・コンポーネントを新たに定義する場合は、このファイルを先に更新する。

---

## デザイン原則

1. **明瞭性** — 情報の優先度を視覚的に明確にする
2. **一貫性** — 同じ操作には同じUIパターンを使う
3. **最小性** — 必要な情報のみ表示し、認知負荷を下げる
4. **アクセシビリティ** — WCAG 2.1 AA 準拠、SP必須対応

---

## カラートークン

| トークン | 値 | 用途 |
|---|---|---|
| `--color-primary` | `#2563eb` | メインアクション・リンク・選択状態 |
| `--color-primary-light` | `#dbeafe` | 選択状態の背景 |
| `--color-success` | `#16a34a` | 成功・有効・一般ユーザーバッジ |
| `--color-warning` | `#d97706` | 注意・警告 |
| `--color-danger` | `#dc2626` | エラー・削除・スーパー管理者バッジ |
| `--color-bg` | `#f8fafc` | ページ背景 |
| `--color-surface` | `#ffffff` | カード・ナビ・モーダル背景 |
| `--color-border` | `#e2e8f0` | 区切り線・枠線 |
| `--color-text` | `#1e293b` | 本文 |
| `--color-text-muted` | `#64748b` | 補足テキスト・ラベル |
| `--color-text-inverse` | `#ffffff` | 暗背景上のテキスト |

### ロールバッジカラー

| ロール | バッジカラー |
|---|---|
| `super_admin` | `--color-danger` |
| `tenant_admin` | `--color-primary` |
| `user` | `--color-success` |

---

## スペーシング（4px基準）

| 変数 | 値 | 主な用途 |
|---|---|---|
| `--space-1` | `4px` | アイコン間隔 |
| `--space-2` | `8px` | インライン要素間 |
| `--space-3` | `12px` | コンパクト要素間 |
| `--space-4` | `16px` | 標準余白 |
| `--space-6` | `24px` | セクション内余白 |
| `--space-8` | `32px` | セクション間 |

---

## タイポグラフィ

| 用途 | サイズ | ウェイト |
|---|---|---|
| ページタイトル | `1.5rem` | 700 |
| セクション見出し | `1.125rem` | 600 |
| 本文 | `1rem` | 400 |
| 補足・ラベル | `0.875rem` | 400〜500 |
| バッジ・キャプション | `0.75rem` | 600 |

フォント: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`

---

## レイアウト

| 要素 | 値 |
|---|---|
| トップバー高さ | `60px` |
| サイドナビ幅（PC） | `220px` |
| コンテンツ最大幅 | `720px` |
| SP ブレークポイント | `768px` |

---

## コンポーネント一覧

### 基本部品（Atoms）

| コンポーネント | props | 備考 |
|---|---|---|
| `Button` | `variant: primary\|secondary\|danger\|ghost`, `size: sm\|md\|lg`, `icon`, `disabled` | タップ最小44px |
| `Badge` | `label`, `color` | `role="status"` |
| `Avatar` | `initial`, `size`, `src` | 画像なし時はイニシャル表示 |
| `Spinner` | `size` | `role="status"` |

### 複合部品（Molecules）

| コンポーネント | 構成 | 備考 |
|---|---|---|
| `UserDropdown` | Avatar + Badge + DropdownMenu | `aria-haspopup`, `aria-expanded` |
| `NavItem` | Icon + Label | `aria-current="page"` で選択状態 |
| `FormField` | Label + Input + ErrorMessage | `htmlFor` 必須 |
| `InfoRow` | Label + Value | テーブル的な情報表示 |

### 構造部品（Organisms）

| コンポーネント | 役割 | SP対応 |
|---|---|---|
| `TopBar` | ロゴ + UserDropdown | ハンバーガー追加 |
| `SideNav` | ナビゲーションリスト | 非表示（ドロワーに切り替え） |
| `MobileDrawer` | SP用サイドナビ | オーバーレイ表示 |
| `PageHeader` | タイトル + アクション | タイトルのみ縦積み |

### 汎用部品

| コンポーネント | 用途 |
|---|---|
| `Card` | コンテンツブロック |
| `Alert` | `type: success\|warning\|error\|info` |
| `Modal` | ダイアログ、`aria-modal` |
| `Table` | データ一覧、モバイルはカード表示 |
| `EmptyState` | データなし表示 |

---

## アクセシビリティ要件

- セマンティックHTML必須（`<header>`, `<main>`, `<nav>`, `<section>`, `<form>`）
- 全インタラクティブ要素に `aria-label` または可視テキスト
- キーボード操作対応（`:focus-visible` スタイルあり）
- `Escape` でモーダル・ドロップダウンを閉じる
- エラーは `role="alert"` で通知

---

## SP 対応ルール（必須）

- `768px` 以下でモバイルレイアウト切り替え
- タップターゲット最小 44×44px
- 横スクロール禁止
- フォント最小 14px（`0.875rem`）
- サイドナビ → MobileDrawer
- テーブル → カード形式
- 余白 24px → 16px
