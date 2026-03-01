---
name: test-runner
description: テストを実行し、結果を分析してレビュー・修正を行う。単体・統合・E2Eテストを分離実行可能。
---

# Test Runner — テスト実行・分析・修正

## 概要

pytestを使用してテストを実行し、結果を分析・レビューする。
失敗したテストは自動的に修正を試み、再実行する。

## テスト分類

| レベル | マーカー | 対象 | 実行時間 |
|---|---|---|---|
| 単体テスト | `@pytest.mark.unit` | 個別モジュール・関数 | 秒単位 |
| 統合テスト | `@pytest.mark.integration` | 複数コンポーネント統合 | 数秒〜数十秒 |
| E2Eテスト | `@pytest.mark.e2e` | 実環境での完全フロー | 分単位 |

## コマンド

### /test (単体テストのみ)

```bash
pytest tests/unit/ -v --tb=short
```

最も高速。個別モジュールのロジックを検証。

### /test --integration (統合テスト)

```bash
pytest tests/integration/ -v --tb=short
```

複数コンポーネントの連携を検証。

### /test --e2e (E2Eテスト)

```bash
pytest tests/e2e/ -v --tb=short
```

実環境（Auth Stack起動）での完全フローを検証。

### /test --all (全テスト)

```bash
pytest tests/ -v --tb=short
```

全レベルのテストを実行。CI/CD用。

### /test --failed (失敗したテストのみ再実行)

```bash
pytest --lf -v
```

前回失敗したテストのみを再実行。

## テスト実行ワークフロー

### Phase 1: テスト実行

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST RUNNER — 実行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

実行対象: tests/unit/
実行コマンド: pytest tests/unit/ -v --tb=short

結果: 11 passed, 0 failed
カバレッジ: 85%
実行時間: 2.3s
```

### Phase 2: 結果分析

失敗したテストがある場合、以下を分析：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST RUNNER — 分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

失敗テスト: 3件

1. test_jwks_service_fetch_success
   原因: AsyncMockの設定ミス
   エラー: AssertionError: coroutine != dict
   
2. test_jwt_auth_valid_token
   原因: モックが正しく動作していない
   エラー: 401 == 200
   
3. test_cache_expiry
   原因: JWKS_CACHE_TTL最小値制約（60秒）
   エラー: ValidationError: ge=60
```

### Phase 3: 自動修正

失敗理由に基づいて修正を試みる：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST RUNNER — 修正
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

修正1: tests/unit/test_jwks_service.py
  - mock_response.json.return_value → AsyncMock(return_value=...)
  
修正2: tests/unit/test_jwks_service.py
  - JWKS_CACHE_TTL="1" → JWKS_CACHE_TTL="60"
  
修正3: src/common_auth/config.py
  - ge=60 → ge=1 (テスト用に制約緩和)
```

### Phase 4: 再テスト

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST RUNNER — 再実行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

実行コマンド: pytest --lf -v

結果: 3 passed, 0 failed
全テスト: 14 passed, 0 failed ✅
```

## 実装ロジック

### 1. テスト実行

```python
import subprocess

def run_tests(level: str = "unit") -> dict:
    """
    テストを実行して結果を返す。
    
    Args:
        level: "unit", "integration", "e2e", "all"
    """
    test_dir = {
        "unit": "tests/unit/",
        "integration": "tests/integration/",
        "e2e": "tests/e2e/",
        "all": "tests/"
    }[level]
    
    result = subprocess.run(
        ["pytest", test_dir, "-v", "--tb=short", "--json-report"],
        capture_output=True,
        text=True
    )
    
    return parse_test_results(result.stdout)
```

### 2. 失敗テスト分析

```python
def analyze_failures(test_results: dict) -> list:
    """
    失敗したテストを分析し、修正方針を決定。
    """
    failures = []
    
    for test in test_results["failed"]:
        failure_info = {
            "test_name": test["name"],
            "error_type": classify_error(test["error"]),
            "fix_strategy": determine_fix_strategy(test),
            "files_to_modify": get_relevant_files(test)
        }
        failures.append(failure_info)
    
    return failures
```

### 3. 自動修正

```python
def auto_fix_tests(failures: list) -> list:
    """
    失敗したテストを自動修正。
    """
    fixed = []
    
    for failure in failures:
        if failure["error_type"] == "async_mock":
            fix_async_mock(failure["files_to_modify"])
            fixed.append(failure["test_name"])
        elif failure["error_type"] == "validation_error":
            fix_validation_constraint(failure)
            fixed.append(failure["test_name"])
    
    return fixed
```

## エラーパターンと修正戦略

| エラータイプ | 検出パターン | 修正戦略 |
|---|---|---|
| AsyncMock設定ミス | `coroutine object` in error | `.return_value` → `AsyncMock(return_value=...)` |
| モック未await | `was never awaited` | `mock.return_value` → `await mock()` |
| バリデーションエラー | `ValidationError` | 制約を緩和、またはテストデータを修正 |
| 環境変数不足 | `ConfigurationError` | `.env` または `monkeypatch` を確認 |
| Import エラー | `ModuleNotFoundError` | 依存関係をインストール |

## 出力フォーマット

### テスト成功時

```markdown
✅ テスト成功

実行: tests/unit/ (11 tests)
結果: 11 passed, 0 failed
カバレッジ: 94%
実行時間: 2.1s

次のアクション: 統合テストを実行 (`/test --integration`)
```

### テスト失敗時

```markdown
❌ テスト失敗

実行: tests/unit/ (14 tests)
結果: 11 passed, 3 failed

失敗テスト:
1. test_jwks_service_fetch_success
   - 原因: AsyncMockの設定ミス
   - 修正: mock_response.json = AsyncMock(return_value=jwks_response)
   
2. test_cache_expiry_triggers_refresh
   - 原因: JWKS_CACHE_TTL最小値制約
   - 修正: テストで60秒以上を使用

修正を自動適用しますか？ (y/n)
```

### 修正後の再テスト

```markdown
🔄 再テスト実行

修正適用: 3ファイル
- tests/unit/test_jwks_service.py
- src/common_auth/config.py

再実行: pytest --lf -v
結果: 3 passed, 0 failed ✅

全テスト状況: 14 passed, 0 failed
カバレッジ: 87%

次のアクション: コミット可能な状態です (`/push`)
```

## テストカバレッジ目標

| コンポーネント | 目標 | 現状 | 状態 |
|---|---|---|---|
| config.py | 90% | 94% | ✅ |
| jwks.py | 90% | 60% | ⚠️ |
| jwt_auth.py | 80% | 23% | ❌ |
| middleware | 80% | 40-50% | ⚠️ |
| routers | 80% | 55% | ⚠️ |
| **全体** | **85%** | **56%** | ⚠️ |

## テストログの記録

テスト結果は `docs/test/logs/` に記録：

```
docs/test/logs/
├── 2026-03-01_180000_unit_tests.md
├── 2026-03-01_180130_unit_tests_retry.md
└── 2026-03-01_181000_integration_tests.md
```

各ログには以下を含む：
- 実行日時・対象
- 結果サマリー（passed/failed/skipped）
- 失敗テストの詳細
- 修正内容
- カバレッジ情報

## 使用例

### Example 1: 単体テストのみ実行

```
User: /test

AI:
1. pytest tests/unit/ -v を実行
2. 結果を分析
3. 失敗があれば原因を特定
4. 修正を提案
5. 再テスト
```

### Example 2: 失敗したテストのみ修正

```
User: /test --failed

AI:
1. pytest --lf を実行（前回失敗分のみ）
2. 結果を確認
3. 全て合格なら完了
```

### Example 3: カバレッジ向上

```
User: /test --coverage

AI:
1. pytest --cov=src --cov-report=html を実行
2. カバレッジレポートを分析
3. 未カバー箇所を特定
4. テスト追加を提案
```
