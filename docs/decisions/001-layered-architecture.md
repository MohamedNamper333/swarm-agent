# ADR-001: Layered Architecture + Strict Boundaries

## Status
**Accepted** — 2025-08-24

## Context
The Swarm Enterprise Platform initially had a "God Object" anti-pattern where `SwarmMaster` imported 15+ core modules directly. This created:
- 65+ layer architecture violations (detected by import-linter)
- 15+ circular dependencies
- Tight coupling making testing impossible
- Single point of failure

## Decision
Implement strict layered architecture with 4 layers:

```
Layer 4 (Applications): board, csuite, code, design, video, research, data, language, knowledge, safety
Layer 3 (Services):     core.job, core.memory, core.observability, core.security
Layer 2 (Platform):     core.plane, core.orchestration, core.execution
Layer 1 (Foundation):   core.auth, core.budget, core.routing, core.policy
```

Rules:
- Layer N can only import from Layer N-1 and below
- No circular imports allowed
- All cross-cutting concerns use `core/contracts/` interfaces
- SwarmMaster uses ServiceRegistry + Lazy Loading (importlib) instead of direct imports

## Consequences

### Positive
- Clear dependency graph: `import-linter lint` passes with 0 violations
- Each layer can be tested independently
- Modules can be deployed independently
- Reduced blast radius for failures

### Negative
- More boilerplate (interfaces, adapters, lazy loading)
- Slightly more complex initialization
- Developers must understand layer boundaries

### Neutral
- Import-linter config in `importlinter.toml` serves as living documentation
- CI gate prevents regression automatically
