# ADR-009: Import-Linter as CI Gate

## Status
**Accepted** — 2025-08-24

## Context
The codebase had 80+ layer architecture violations and 15+ circular dependencies. These were only discovered through manual analysis. Without automated enforcement, violations would accumulate again.

## Decision
Use `import-linter` as a mandatory CI gate that:
1. Defines 5 contracts (Layer Architecture, Module Independence, SwarmMaster Independence, Department Independence, Tests Independence)
2. Fails the build if any contract is violated
3. Prevents merge of PRs that introduce new violations
4. Uses TOML format (`importlinter.toml`) for configuration

### Implementation Files
- `importlinter.toml` — Contract definitions
- `.github/workflows/ci.yml` — CI pipeline with import-linter gate

## Consequences

### Positive
- Architectural violations caught immediately at PR time
- Self-documenting architecture (contracts describe allowed dependencies)
- No manual review needed for import violations
- Regression prevention is automatic

### Negative
- Initial setup required significant refactoring (80+ fixes)
- False positives possible with dynamic imports (mitigated by using `importlib.import_module`)
- Adds ~30s to CI pipeline

### Neutral
- Contracts can be temporarily relaxed with documented justification
- `--contract` flag allows checking specific contracts during development
