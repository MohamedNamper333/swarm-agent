# swarm-agent Makefile
# Convenience targets for the most common dev / CI / deploy workflows.

SHELL := /bin/bash
PY   := python3
PIP  := $(PY) -m pip
PYTEST := $(PY) -m pytest

# Always run tests with project root on PYTHONPATH so `swarm.*` and `vault_client` import.
export PYTHONPATH := $(PWD)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- install -----------------------------------------------------------------

.PHONY: install
install: ## Install package + dev extras.
	$(PIP) install -e ".[dev]"

.PHONY: install-all
install-all: ## Install everything (dev + dashboard + vault).
	$(PIP) install -e ".[all]"

# --- test --------------------------------------------------------------------

.PHONY: test
test: ## Run all test suites (unit + live + stress + e2e).
	$(PYTEST) tests/ -q --no-header

.PHONY: test-unit
test-unit: ## Run unit tests only.
	$(PYTEST) tests/unit/ -q --no-header

.PHONY: test-live
test-live: ## Run live / live pipeline tests.
	$(PYTEST) tests/live/ -q --no-header

.PHONY: test-stress
test-stress: ## Run stress / load tests.
	$(PYTEST) tests/stress/ -v --no-header

.PHONY: test-e2e
test-e2e: ## Run e2e integration tests.
	$(PYTEST) tests/e2e/ -v --no-header

.PHONY: test-cov
test-cov: ## Run tests with coverage report.
	$(PYTEST) tests/unit/ tests/live/ tests/stress/ --cov=swarm --cov-report=term-missing --cov-report=html --no-header

# --- lint / type -------------------------------------------------------------

.PHONY: lint
lint: ## Run ruff on the swarm package.
	$(PY) -m ruff check swarm/ || true

.PHONY: typecheck
typecheck: ## Run mypy on the swarm package.
	$(PY) -m mypy swarm/ || true

.PHONY: format
format: ## Auto-format with ruff.
	$(PY) -m ruff format swarm/ || true

# --- dashboard ---------------------------------------------------------------

.PHONY: dashboard
dashboard: ## Start the Modern Dark Cinema dashboard (Vite + React).
	cd dashboard/web && npm run dev

.PHONY: dashboard-build
dashboard-build: ## Build the dashboard for production.
	cd dashboard/web && npm run build

# --- vault -------------------------------------------------------------------

.PHONY: vault
vault: ## Start the local vault server on :8088.
	$(PY) -m vault.server &

# --- ci ----------------------------------------------------------------------

.PHONY: ci
ci: test-unit test-stress lint typecheck ## Run the full CI gauntlet locally.
	@echo "✅ CI gauntlet complete"

# --- clean -------------------------------------------------------------------

.PHONY: clean
clean: ## Remove build / cache artifacts.
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-all
clean-all: clean ## Also remove node_modules and dashboard build output.
	rm -rf dashboard/web/node_modules dashboard/web/dist dashboard/web/.vite

# --- info --------------------------------------------------------------------

.PHONY: info
info: ## Show environment + package metadata.
	@echo "Python:  $$($(PY) --version)"
	@echo "Pip:     $$($(PIP) --version)"
	@echo "Pytest:  $$($(PY) -m pytest --version)"
	@echo "Project: $$($(PY) -c 'import tomllib; print(tomllib.load(open(\"pyproject.toml\",\"rb\"))[\"project\"][\"name\"], tomllib.load(open(\"pyproject.toml\",\"rb\"))[\"project\"][\"version\"])')"
