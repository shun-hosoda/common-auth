# レビュー時の型チェック・テストコマンド

## TypeScript 型チェック

```powershell
# Frontend SDK
npx tsc --noEmit -p packages/frontend-sdk/tsconfig.json

# React Example App
npx tsc --noEmit -p examples/react-app/tsconfig.json
```

## Python 型チェック

```powershell
cd packages/backend-sdk
python -m mypy src/ --ignore-missing-imports 2>&1 | Select-Object -Last 5
```

## テスト実行

```powershell
# Frontend SDK（Jest）
cd packages/frontend-sdk
npx jest --coverage

# React Example App（Vitest）
cd examples/react-app
npx vitest run

# Backend SDK（pytest）
cd packages/backend-sdk
python -m pytest tests/ -v
```

## /push 時のステージング対象

```powershell
# 変更に .tsx/.jsx/.ts が含まれる場合
npx tsc --noEmit -p packages/frontend-sdk/tsconfig.json
npx tsc --noEmit -p examples/react-app/tsconfig.json

# 変更に .py が含まれる場合
cd packages/backend-sdk; python -m mypy src/ --ignore-missing-imports
```
