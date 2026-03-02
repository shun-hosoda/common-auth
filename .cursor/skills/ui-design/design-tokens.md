# Design Tokens Reference

## CSS カスタムプロパティ（全量）

```css
:root {
  /* === Colors === */
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-primary-light: #dbeafe;

  --color-secondary: #64748b;
  --color-secondary-dark: #475569;
  --color-secondary-light: #f1f5f9;

  --color-success: #16a34a;
  --color-success-light: #dcfce7;
  --color-warning: #d97706;
  --color-warning-light: #fef3c7;
  --color-danger: #dc2626;
  --color-danger-light: #fee2e2;
  --color-info: #0284c7;
  --color-info-light: #e0f2fe;

  /* === Surfaces === */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-hover: #f8fafc;
  --color-border: #e2e8f0;
  --color-border-focus: #2563eb;

  /* === Text === */
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-text-disabled: #94a3b8;
  --color-text-inverse: #ffffff;

  /* === Spacing === */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;

  /* === Typography === */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-lg: 1.125rem;  /* 18px */
  --font-size-xl: 1.25rem;   /* 20px */
  --font-size-2xl: 1.5rem;   /* 24px */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;

  /* === Border Radius === */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* === Shadows === */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);

  /* === Layout === */
  --topbar-height: 64px;
  --sidebar-width: 240px;
  --content-max-width: 1200px;

  /* === Transitions === */
  --transition-fast: 150ms ease;
  --transition-base: 250ms ease;
}

/* ダークモード */
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f172a;
    --color-surface: #1e293b;
    --color-surface-hover: #334155;
    --color-border: #334155;
    --color-text: #f1f5f9;
    --color-text-muted: #94a3b8;
  }
}
```

## ロールバッジカラーマッピング

```
super_admin  → danger  (#dc2626)
tenant_admin → primary (#2563eb)
user         → success (#16a34a)
```
