# swarm-agent Makefile
# Convenience targets for development, verification and release.

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
install: ## Install package + dev extras.
	$(PIP) install -e ".[dev]"

.PHONY: install-all
install-all: ## Install all optional extras.
	$(PIP) install -e ".[all]"

.PHONY: test
test: ## Run the complete test tree.
	$(PYTEST) tests/ -q --no-header

.PHONY: test-unit
test-unit: ## Run unit tests.
	$(PYTEST) tests/unit/ -q --no-header

.PHONY: test-enterprise
test-enterprise: ## Run enterprise and architectural tests.
	$(PYTEST) tests/enterprise/ -q --no-header

.PHONY: test-stress
test-stress: ## Run stress and recovery tests.
	$(PYTEST) tests/stress/ -v --no-header

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests.
	$(PYTEST) tests/e2e/ -v --no-header

.PHONY: test-cov
test-cov: ## Run tests with coverage.
	$(PYTEST) tests/unit/ tests/enterprise/ tests/stress/ --cov=swarm --cov-report=term-missing --cov-report=html --no-header

.PHONY: lint
lint: ## Run Ruff without suppressing failures.
	$(PY) -m ruff check swarm tests

.PHONY: typecheck
typecheck: ## Run mypy without suppressing failures.
	$(PY) -m mypy swarm

.PHONY: verify-invariants
verify-invariants: ## Verify all 18 architectural invariants.
	$(PY) scripts/verify_invariants.py

.PHONY: scan-secrets
scan-secrets: ## Run fail-closed repository secret scan.
	$(PY) scripts/scan_secrets.py

.PHONY: production-gate
production-gate: ## Execute the fail-closed production release gate.
	$(PY) scripts/run_production_gate.py

.PHONY: ci
ci: lint test-unit test-enterprise verify-invariants scan-secrets test-stress ## Run the local CI gauntlet.
	@echo "CI verification complete"

.PHONY: clean
clean: ## Remove Python build and cache artifacts.
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov/ .coverage artifacts/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

.PHONY: info
info: ## Show environment and package metadata.
	@echo "Python:  $$($(PY) --version)"
	@echo "Pip:     $$($(PIP) --version)"
	@echo "Pytest:  $$($(PY) -m pytest --version)"
	@echo "Project: $$($(PY) -c 'import tomllib; d=tomllib.load(open(\"pyproject.toml\",\"rb\")); print(d[\"project\"][\"name\"], d[\"project\"][\"version\"])')"
