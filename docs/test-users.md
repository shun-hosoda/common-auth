# テストユーザー一覧

> このファイルは `scripts/seed-test-users.ps1` で作成されるテストユーザーの一覧です。
> **本番環境には絶対に使用しないでください。**

## 初期ユーザー（realm-export.json に含まれる）

| ユーザー名 | パスワード | ロール | テナント | 備考 |
|-----------|----------|--------|---------|------|
| `super_admin@example.com` | `superadmin123` | super_admin | - | 全テナント管理者 |
| `admin_acme-corp@example.com` | `admin123` | tenant_admin | acme-corp | テナント管理者 |
| `testuser_acme-corp@example.com` | `password123` | user | acme-corp | 一般ユーザー |
| `emailmfa_acme-corp@example.com` | `password123` | user | acme-corp | Email MFA有効ユーザー |
| `admin_globex-inc@example.com` | `admin123` | tenant_admin | globex-inc | テナント管理者 |
| `testuser_globex-inc@example.com` | `password123` | user | globex-inc | 一般ユーザー |

## seed スクリプトで作成されるユーザー

実行コマンド:
```powershell
.\scripts\seed-test-users.ps1
```

### acme-corp テストユーザー（100件）

| ユーザー名 | パスワード | ロール | テナント |
|-----------|----------|--------|---------|
| `user001_acme-corp@example.com` | `password123` | user | acme-corp |
| `user002_acme-corp@example.com` | `password123` | user | acme-corp |
| `user003_acme-corp@example.com` | `password123` | user | acme-corp |
| `user004_acme-corp@example.com` | `password123` | user | acme-corp |
| `user005_acme-corp@example.com` | `password123` | user | acme-corp |
| `user006_acme-corp@example.com` | `password123` | user | acme-corp |
| `user007_acme-corp@example.com` | `password123` | user | acme-corp |
| `user008_acme-corp@example.com` | `password123` | user | acme-corp |
| `user009_acme-corp@example.com` | `password123` | user | acme-corp |
| `user010_acme-corp@example.com` | `password123` | user | acme-corp |
| `user011_acme-corp@example.com` | `password123` | user | acme-corp |
| `user012_acme-corp@example.com` | `password123` | user | acme-corp |
| `user013_acme-corp@example.com` | `password123` | user | acme-corp |
| `user014_acme-corp@example.com` | `password123` | user | acme-corp |
| `user015_acme-corp@example.com` | `password123` | user | acme-corp |
| `user016_acme-corp@example.com` | `password123` | user | acme-corp |
| `user017_acme-corp@example.com` | `password123` | user | acme-corp |
| `user018_acme-corp@example.com` | `password123` | user | acme-corp |
| `user019_acme-corp@example.com` | `password123` | user | acme-corp |
| `user020_acme-corp@example.com` | `password123` | user | acme-corp |
| `user021_acme-corp@example.com` | `password123` | user | acme-corp |
| `user022_acme-corp@example.com` | `password123` | user | acme-corp |
| `user023_acme-corp@example.com` | `password123` | user | acme-corp |
| `user024_acme-corp@example.com` | `password123` | user | acme-corp |
| `user025_acme-corp@example.com` | `password123` | user | acme-corp |
| `user026_acme-corp@example.com` | `password123` | user | acme-corp |
| `user027_acme-corp@example.com` | `password123` | user | acme-corp |
| `user028_acme-corp@example.com` | `password123` | user | acme-corp |
| `user029_acme-corp@example.com` | `password123` | user | acme-corp |
| `user030_acme-corp@example.com` | `password123` | user | acme-corp |
| `user031_acme-corp@example.com` | `password123` | user | acme-corp |
| `user032_acme-corp@example.com` | `password123` | user | acme-corp |
| `user033_acme-corp@example.com` | `password123` | user | acme-corp |
| `user034_acme-corp@example.com` | `password123` | user | acme-corp |
| `user035_acme-corp@example.com` | `password123` | user | acme-corp |
| `user036_acme-corp@example.com` | `password123` | user | acme-corp |
| `user037_acme-corp@example.com` | `password123` | user | acme-corp |
| `user038_acme-corp@example.com` | `password123` | user | acme-corp |
| `user039_acme-corp@example.com` | `password123` | user | acme-corp |
| `user040_acme-corp@example.com` | `password123` | user | acme-corp |
| `user041_acme-corp@example.com` | `password123` | user | acme-corp |
| `user042_acme-corp@example.com` | `password123` | user | acme-corp |
| `user043_acme-corp@example.com` | `password123` | user | acme-corp |
| `user044_acme-corp@example.com` | `password123` | user | acme-corp |
| `user045_acme-corp@example.com` | `password123` | user | acme-corp |
| `user046_acme-corp@example.com` | `password123` | user | acme-corp |
| `user047_acme-corp@example.com` | `password123` | user | acme-corp |
| `user048_acme-corp@example.com` | `password123` | user | acme-corp |
| `user049_acme-corp@example.com` | `password123` | user | acme-corp |
| `user050_acme-corp@example.com` | `password123` | user | acme-corp |
| `user051_acme-corp@example.com` | `password123` | user | acme-corp |
| `user052_acme-corp@example.com` | `password123` | user | acme-corp |
| `user053_acme-corp@example.com` | `password123` | user | acme-corp |
| `user054_acme-corp@example.com` | `password123` | user | acme-corp |
| `user055_acme-corp@example.com` | `password123` | user | acme-corp |
| `user056_acme-corp@example.com` | `password123` | user | acme-corp |
| `user057_acme-corp@example.com` | `password123` | user | acme-corp |
| `user058_acme-corp@example.com` | `password123` | user | acme-corp |
| `user059_acme-corp@example.com` | `password123` | user | acme-corp |
| `user060_acme-corp@example.com` | `password123` | user | acme-corp |
| `user061_acme-corp@example.com` | `password123` | user | acme-corp |
| `user062_acme-corp@example.com` | `password123` | user | acme-corp |
| `user063_acme-corp@example.com` | `password123` | user | acme-corp |
| `user064_acme-corp@example.com` | `password123` | user | acme-corp |
| `user065_acme-corp@example.com` | `password123` | user | acme-corp |
| `user066_acme-corp@example.com` | `password123` | user | acme-corp |
| `user067_acme-corp@example.com` | `password123` | user | acme-corp |
| `user068_acme-corp@example.com` | `password123` | user | acme-corp |
| `user069_acme-corp@example.com` | `password123` | user | acme-corp |
| `user070_acme-corp@example.com` | `password123` | user | acme-corp |
| `user071_acme-corp@example.com` | `password123` | user | acme-corp |
| `user072_acme-corp@example.com` | `password123` | user | acme-corp |
| `user073_acme-corp@example.com` | `password123` | user | acme-corp |
| `user074_acme-corp@example.com` | `password123` | user | acme-corp |
| `user075_acme-corp@example.com` | `password123` | user | acme-corp |
| `user076_acme-corp@example.com` | `password123` | user | acme-corp |
| `user077_acme-corp@example.com` | `password123` | user | acme-corp |
| `user078_acme-corp@example.com` | `password123` | user | acme-corp |
| `user079_acme-corp@example.com` | `password123` | user | acme-corp |
| `user080_acme-corp@example.com` | `password123` | user | acme-corp |
| `user081_acme-corp@example.com` | `password123` | user | acme-corp |
| `user082_acme-corp@example.com` | `password123` | user | acme-corp |
| `user083_acme-corp@example.com` | `password123` | user | acme-corp |
| `user084_acme-corp@example.com` | `password123` | user | acme-corp |
| `user085_acme-corp@example.com` | `password123` | user | acme-corp |
| `user086_acme-corp@example.com` | `password123` | user | acme-corp |
| `user087_acme-corp@example.com` | `password123` | user | acme-corp |
| `user088_acme-corp@example.com` | `password123` | user | acme-corp |
| `user089_acme-corp@example.com` | `password123` | user | acme-corp |
| `user090_acme-corp@example.com` | `password123` | user | acme-corp |
| `user091_acme-corp@example.com` | `password123` | user | acme-corp |
| `user092_acme-corp@example.com` | `password123` | user | acme-corp |
| `user093_acme-corp@example.com` | `password123` | user | acme-corp |
| `user094_acme-corp@example.com` | `password123` | user | acme-corp |
| `user095_acme-corp@example.com` | `password123` | user | acme-corp |
| `user096_acme-corp@example.com` | `password123` | user | acme-corp |
| `user097_acme-corp@example.com` | `password123` | user | acme-corp |
| `user098_acme-corp@example.com` | `password123` | user | acme-corp |
| `user099_acme-corp@example.com` | `password123` | user | acme-corp |
| `user100_acme-corp@example.com` | `password123` | user | acme-corp |

### globex-inc テストユーザー（100件）

| ユーザー名 | パスワード | ロール | テナント |
|-----------|----------|--------|---------|
| `user001_globex-inc@example.com` | `password123` | user | globex-inc |
| `user002_globex-inc@example.com` | `password123` | user | globex-inc |
| `user003_globex-inc@example.com` | `password123` | user | globex-inc |
| `user004_globex-inc@example.com` | `password123` | user | globex-inc |
| `user005_globex-inc@example.com` | `password123` | user | globex-inc |
| `user006_globex-inc@example.com` | `password123` | user | globex-inc |
| `user007_globex-inc@example.com` | `password123` | user | globex-inc |
| `user008_globex-inc@example.com` | `password123` | user | globex-inc |
| `user009_globex-inc@example.com` | `password123` | user | globex-inc |
| `user010_globex-inc@example.com` | `password123` | user | globex-inc |
| `user011_globex-inc@example.com` | `password123` | user | globex-inc |
| `user012_globex-inc@example.com` | `password123` | user | globex-inc |
| `user013_globex-inc@example.com` | `password123` | user | globex-inc |
| `user014_globex-inc@example.com` | `password123` | user | globex-inc |
| `user015_globex-inc@example.com` | `password123` | user | globex-inc |
| `user016_globex-inc@example.com` | `password123` | user | globex-inc |
| `user017_globex-inc@example.com` | `password123` | user | globex-inc |
| `user018_globex-inc@example.com` | `password123` | user | globex-inc |
| `user019_globex-inc@example.com` | `password123` | user | globex-inc |
| `user020_globex-inc@example.com` | `password123` | user | globex-inc |
| `user021_globex-inc@example.com` | `password123` | user | globex-inc |
| `user022_globex-inc@example.com` | `password123` | user | globex-inc |
| `user023_globex-inc@example.com` | `password123` | user | globex-inc |
| `user024_globex-inc@example.com` | `password123` | user | globex-inc |
| `user025_globex-inc@example.com` | `password123` | user | globex-inc |
| `user026_globex-inc@example.com` | `password123` | user | globex-inc |
| `user027_globex-inc@example.com` | `password123` | user | globex-inc |
| `user028_globex-inc@example.com` | `password123` | user | globex-inc |
| `user029_globex-inc@example.com` | `password123` | user | globex-inc |
| `user030_globex-inc@example.com` | `password123` | user | globex-inc |
| `user031_globex-inc@example.com` | `password123` | user | globex-inc |
| `user032_globex-inc@example.com` | `password123` | user | globex-inc |
| `user033_globex-inc@example.com` | `password123` | user | globex-inc |
| `user034_globex-inc@example.com` | `password123` | user | globex-inc |
| `user035_globex-inc@example.com` | `password123` | user | globex-inc |
| `user036_globex-inc@example.com` | `password123` | user | globex-inc |
| `user037_globex-inc@example.com` | `password123` | user | globex-inc |
| `user038_globex-inc@example.com` | `password123` | user | globex-inc |
| `user039_globex-inc@example.com` | `password123` | user | globex-inc |
| `user040_globex-inc@example.com` | `password123` | user | globex-inc |
| `user041_globex-inc@example.com` | `password123` | user | globex-inc |
| `user042_globex-inc@example.com` | `password123` | user | globex-inc |
| `user043_globex-inc@example.com` | `password123` | user | globex-inc |
| `user044_globex-inc@example.com` | `password123` | user | globex-inc |
| `user045_globex-inc@example.com` | `password123` | user | globex-inc |
| `user046_globex-inc@example.com` | `password123` | user | globex-inc |
| `user047_globex-inc@example.com` | `password123` | user | globex-inc |
| `user048_globex-inc@example.com` | `password123` | user | globex-inc |
| `user049_globex-inc@example.com` | `password123` | user | globex-inc |
| `user050_globex-inc@example.com` | `password123` | user | globex-inc |
| `user051_globex-inc@example.com` | `password123` | user | globex-inc |
| `user052_globex-inc@example.com` | `password123` | user | globex-inc |
| `user053_globex-inc@example.com` | `password123` | user | globex-inc |
| `user054_globex-inc@example.com` | `password123` | user | globex-inc |
| `user055_globex-inc@example.com` | `password123` | user | globex-inc |
| `user056_globex-inc@example.com` | `password123` | user | globex-inc |
| `user057_globex-inc@example.com` | `password123` | user | globex-inc |
| `user058_globex-inc@example.com` | `password123` | user | globex-inc |
| `user059_globex-inc@example.com` | `password123` | user | globex-inc |
| `user060_globex-inc@example.com` | `password123` | user | globex-inc |
| `user061_globex-inc@example.com` | `password123` | user | globex-inc |
| `user062_globex-inc@example.com` | `password123` | user | globex-inc |
| `user063_globex-inc@example.com` | `password123` | user | globex-inc |
| `user064_globex-inc@example.com` | `password123` | user | globex-inc |
| `user065_globex-inc@example.com` | `password123` | user | globex-inc |
| `user066_globex-inc@example.com` | `password123` | user | globex-inc |
| `user067_globex-inc@example.com` | `password123` | user | globex-inc |
| `user068_globex-inc@example.com` | `password123` | user | globex-inc |
| `user069_globex-inc@example.com` | `password123` | user | globex-inc |
| `user070_globex-inc@example.com` | `password123` | user | globex-inc |
| `user071_globex-inc@example.com` | `password123` | user | globex-inc |
| `user072_globex-inc@example.com` | `password123` | user | globex-inc |
| `user073_globex-inc@example.com` | `password123` | user | globex-inc |
| `user074_globex-inc@example.com` | `password123` | user | globex-inc |
| `user075_globex-inc@example.com` | `password123` | user | globex-inc |
| `user076_globex-inc@example.com` | `password123` | user | globex-inc |
| `user077_globex-inc@example.com` | `password123` | user | globex-inc |
| `user078_globex-inc@example.com` | `password123` | user | globex-inc |
| `user079_globex-inc@example.com` | `password123` | user | globex-inc |
| `user080_globex-inc@example.com` | `password123` | user | globex-inc |
| `user081_globex-inc@example.com` | `password123` | user | globex-inc |
| `user082_globex-inc@example.com` | `password123` | user | globex-inc |
| `user083_globex-inc@example.com` | `password123` | user | globex-inc |
| `user084_globex-inc@example.com` | `password123` | user | globex-inc |
| `user085_globex-inc@example.com` | `password123` | user | globex-inc |
| `user086_globex-inc@example.com` | `password123` | user | globex-inc |
| `user087_globex-inc@example.com` | `password123` | user | globex-inc |
| `user088_globex-inc@example.com` | `password123` | user | globex-inc |
| `user089_globex-inc@example.com` | `password123` | user | globex-inc |
| `user090_globex-inc@example.com` | `password123` | user | globex-inc |
| `user091_globex-inc@example.com` | `password123` | user | globex-inc |
| `user092_globex-inc@example.com` | `password123` | user | globex-inc |
| `user093_globex-inc@example.com` | `password123` | user | globex-inc |
| `user094_globex-inc@example.com` | `password123` | user | globex-inc |
| `user095_globex-inc@example.com` | `password123` | user | globex-inc |
| `user096_globex-inc@example.com` | `password123` | user | globex-inc |
| `user097_globex-inc@example.com` | `password123` | user | globex-inc |
| `user098_globex-inc@example.com` | `password123` | user | globex-inc |
| `user099_globex-inc@example.com` | `password123` | user | globex-inc |
| `user100_globex-inc@example.com` | `password123` | user | globex-inc |