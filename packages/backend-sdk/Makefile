.PHONY: help test test-unit test-integration test-e2e test-all test-failed test-coverage test-quick clean install lint format

# Variables
PYTHON := python
PYTEST := $(PYTHON) -m pytest
PYTHONPATH := src
RUFF := ruff
MYPY := mypy

export PYTHONPATH

# Default target
.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo "Common Auth Backend SDK - Make Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install:  ## Install package in editable mode
	$(PYTHON) -m pip install -e .

install-dev:  ## Install package with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"

# Testing
test: test-unit  ## Run default tests (unit only)

test-unit:  ## Run unit tests
	@echo "Running unit tests..."
	$(PYTEST) tests/unit/ -v --tb=short --no-cov

test-integration:  ## Run integration tests
	@echo "Running integration tests..."
	$(PYTEST) tests/integration/ -v --tb=short --no-cov

test-e2e:  ## Run end-to-end tests
	@echo "Running E2E tests (requires Auth Stack)..."
	$(PYTEST) tests/e2e/ -v --tb=short --no-cov

test-all:  ## Run all tests
	@echo "Running all tests..."
	$(PYTEST) tests/ -v --tb=short

test-failed:  ## Re-run only failed tests
	@echo "Re-running failed tests..."
	$(PYTEST) --lf -v --tb=short

test-quick:  ## Run tests, stop on first failure
	@echo "Running tests (quick mode)..."
	$(PYTEST) tests/unit/ -x -v --tb=short --no-cov

test-coverage:  ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ --cov=src/common_auth --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-watch:  ## Run tests in watch mode (requires pytest-watch)
	$(PYTEST) tests/unit/ -f -v --tb=short --no-cov

# Code Quality
lint:  ## Run linter (ruff)
	@echo "Running ruff..."
	$(RUFF) check src tests

lint-fix:  ## Run linter and auto-fix issues
	@echo "Running ruff with auto-fix..."
	$(RUFF) check --fix src tests

format:  ## Format code with ruff
	@echo "Formatting code..."
	$(RUFF) format src tests

type-check:  ## Run type checker (mypy)
	@echo "Running mypy..."
	$(MYPY) src

# Cleanup
clean:  ## Clean up generated files
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development
dev: install-dev  ## Setup development environment
	@echo "Development environment ready!"

check: lint type-check test-unit  ## Run all checks (lint, type-check, unit tests)
	@echo "All checks passed!"

# CI/CD
ci: lint type-check test-coverage  ## Run CI pipeline (lint, type-check, coverage)
	@echo "CI pipeline completed!"
