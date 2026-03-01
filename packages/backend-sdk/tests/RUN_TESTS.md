# Test Runner Scripts

テスト実行を簡単にするためのヘルパースクリプト。

## PowerShell (Windows)

### test.ps1

```powershell
# Test runner for common-auth backend SDK

param(
    [string]$Level = "unit",
    [switch]$Failed,
    [switch]$Coverage,
    [switch]$Verbose
)

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Base command
$cmd = "python -m pytest"

# Determine test path
switch ($Level) {
    "unit" { $cmd += " tests/unit/" }
    "integration" { $cmd += " tests/integration/" }
    "e2e" { $cmd += " tests/e2e/" }
    "all" { $cmd += " tests/" }
    default { $cmd += " tests/unit/" }
}

# Add flags
if ($Failed) {
    $cmd += " --lf"
}

if ($Verbose) {
    $cmd += " -vv --tb=long"
} else {
    $cmd += " -v --tb=short"
}

if ($Coverage) {
    $cmd += " --cov=src/common_auth --cov-report=html --cov-report=term"
}

# Execute
Write-Host "Running: $cmd" -ForegroundColor Cyan
Invoke-Expression $cmd
```

### 使用方法

```powershell
# 単体テスト
.\test.ps1

# 統合テスト
.\test.ps1 -Level integration

# E2Eテスト
.\test.ps1 -Level e2e

# 全テスト
.\test.ps1 -Level all

# 失敗したテストのみ
.\test.ps1 -Failed

# カバレッジ付き
.\test.ps1 -Coverage

# 詳細出力
.\test.ps1 -Verbose
```

## Bash (Linux/Mac)

### test.sh

```bash
#!/bin/bash
# Test runner for common-auth backend SDK

LEVEL=${1:-unit}
FAILED=${2:-}

export PYTHONPATH="src"

case $LEVEL in
    unit)
        TEST_PATH="tests/unit/"
        ;;
    integration)
        TEST_PATH="tests/integration/"
        ;;
    e2e)
        TEST_PATH="tests/e2e/"
        ;;
    all)
        TEST_PATH="tests/"
        ;;
    *)
        TEST_PATH="tests/unit/"
        ;;
esac

if [ "$FAILED" == "--failed" ]; then
    python -m pytest --lf -v --tb=short
else
    python -m pytest $TEST_PATH -v --tb=short
fi
```

### 使用方法

```bash
# 単体テスト
./test.sh unit

# 統合テスト
./test.sh integration

# E2Eテスト
./test.sh e2e

# 全テスト
./test.sh all

# 失敗したテストのみ
./test.sh unit --failed
```

## Make (任意のOS)

### Makefile

```makefile
.PHONY: test test-unit test-integration test-e2e test-all test-failed test-coverage

PYTHON := python
PYTEST := $(PYTHON) -m pytest
PYTHONPATH := src

export PYTHONPATH

test: test-unit

test-unit:
	$(PYTEST) tests/unit/ -v --tb=short

test-integration:
	$(PYTEST) tests/integration/ -v --tb=short

test-e2e:
	$(PYTEST) tests/e2e/ -v --tb=short

test-all:
	$(PYTEST) tests/ -v --tb=short

test-failed:
	$(PYTEST) --lf -v --tb=short

test-coverage:
	$(PYTEST) tests/ --cov=src/common_auth --cov-report=html --cov-report=term

test-watch:
	$(PYTEST) tests/unit/ -v --tb=short -f
```

### 使用方法

```bash
make test              # 単体テストのみ
make test-integration  # 統合テスト
make test-e2e          # E2Eテスト
make test-all          # 全テスト
make test-failed       # 失敗したテストのみ
make test-coverage     # カバレッジ付き
```

## pytest.ini での設定

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (requires Auth Stack)
    slow: Slow tests (may take minutes)

addopts = 
    --strict-markers
    -v
```

## マーカーを使った実行

```bash
# unitマーカーのテストのみ
pytest -m unit

# integrationマーカーのテストのみ
pytest -m integration

# e2eマーカーのテストのみ
pytest -m e2e

# slowマーカーを除外
pytest -m "not slow"

# unitとintegrationのみ
pytest -m "unit or integration"
```

## CI/CD統合

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd packages/backend-sdk
          pip install -e ".[dev]"
      
      - name: Run unit tests
        run: |
          cd packages/backend-sdk
          pytest tests/unit/ -v
      
      - name: Run integration tests
        run: |
          cd packages/backend-sdk
          pytest tests/integration/ -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```
