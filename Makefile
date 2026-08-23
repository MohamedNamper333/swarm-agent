# swarm-agent Makefile
# Strict developer / CI / release verification targets.

SHELL := /bin/bash
PY   := python3
PIP  := $(PY) -m pip
PYTEST := $(PY) -m pytest
export PYTHONPATH := $(PWD)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install package + development dependencies.
	$(PIP) install -e ".[dev]"

.PHONY: install-all
install-all: ## Install all optional dependencies.
	$(PIP) install -e ".[all]"

.PHONY: test
test: ## Run the complete test suite.
	$(PYTEST) tests/ -q --no-header

.PHONY: test-unit
test-unit: ## Run unit tests.
	$(PYTEST) tests/unit/ -q --no-header

.PHONY: test-enterprise
test-enterprise: ## Run enterprise tests.
	$(PYTEST) tests/enterprise/ -q --no-header

.PHONY: test-live
test-live: ## Run live pipeline tests.
	$(PYTEST) tests/live/ -q --no-header

.PHONY: test-stress
test-stress: ## Run stress and recovery tests.
	$(PYTEST) tests/stress/ -v --no-header

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests.
	$(PYTEST) tests/e2e/ -v --no-header

.PHONY: test-cov
test-cov: ## Run tests with coverage.
	$(PYTEST) tests/unit/ tests/enterprise/ tests/live/ tests/stress/ --cov=swarm --cov-report=term-missing --cov-report=html --no-header

.PHONY: lint
lint: ## Run strict Ruff linting.
	$(PY) -m ruff check swarm tests

.PHONY: typecheck
typecheck: ## Run strict mypy type checking.
	$(PY) -m mypy swarm

.PHONY: format
format: ## Format source with Ruff.
	$(PY) -m ruff format swarm tests

.PHONY: verify-invariants
verify-invariants: ## Verify all 18 architectural invariants fail-closed.
	$(PY) scripts/verify_invariants.py

.PHONY: scan-secrets
scan-secrets: ## Scan repository for exposed secrets.
	$(PY) scripts/scan_secrets.py

.PHONY: dependency-audit
dependency-audit: ## Audit Python dependencies.
	$(PY) -m pip_audit

.PHONY: production-gate
production-gate: ## Execute the complete fail-closed production gate.
	$(PY) scripts/run_production_gate.py --report artifacts/production-gate.json

.PHONY: ci
ci: lint typecheck verify-invariants scan-secrets dependency-audit test-enterprise test-unit test-stress production-gate ## Run the complete local CI/release gauntlet.
	@echo "CI and production gate completed successfully."

.PHONY: dashboard
dashboard: ## Start the dashboard development server.
	cd dashboard/web && npm run dev

.PHONY: dashboard-build
dashboard-build: ## Build the dashboard for production.
	cd dashboard/web && npm run build

.PHONY: vault
vault: ## Start the local vault server on :8088.
	$(PY) -m vault.server

.PHONY: clean
clean: ## Remove Python build/cache artifacts.
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov/ .coverage artifacts/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-all
clean-all: clean ## Also remove dashboard dependencies/build output.
	rm -rf dashboard/web/node_modules dashboard/web/dist dashboard/web/.vite

.PHONY: info
info: ## Show environment and package metadata.
	@echo "Python:  $$($(PY) --version)"
	@echo "Pip:     $$($(PIP) --version)"
	@echo "Pytest:  $$($(PY) -m pytest --version)"
	@echo "Project: $$($(PY) -c 'import tomllib; d=tomllib.load(open("pyproject.toml","rb")); print(d["project"]["name"], d["project"]["version"])')"
