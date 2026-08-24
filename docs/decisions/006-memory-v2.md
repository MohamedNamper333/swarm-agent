# ADR-006: Memory V2 as Context Layer

## Status
**Accepted** — 2025-08-24

## Context
The system needs a unified memory layer for:
- Assembling context for LLM calls (RAG)
- Recording workflow episodes for learning
- Storing lessons learned from failures
- Managing working/episodic/semantic memory layers

## Decision
Use Memory V2 as the single source of truth for all context management:

### Memory Layers
| Layer | Purpose | Trust Level | TTL |
|-------|---------|-------------|-----|
| WORKING | Current conversation state | SYSTEM_VERIFIED | Session |
| EPISODIC | Workflow execution history | AGENT_GENERATED | 7 days |
| SEMANTIC | Learned facts and patterns | HUMAN_REVIEWED | Permanent |
| LESSONS | Failure analysis and corrections | VERIFIED | Permanent |

### Implementation Files
- `memory/v2/fabric.py` — MemoryFabric (main entry point)
- `memory/v2/repository.py` — Memory repository with pluggable backends
- `memory/v2/search.py` — Hybrid search (vector + keyword)
- `memory/v2/context.py` — Context assembly from multiple layers
- `core/memory/enterprise.py` — Enterprise wrapper with tenant isolation

## Consequences

### Positive
- Unified API for all memory operations
- Tenant isolation built into every query
- Trust levels prevent untrusted data from influencing decisions
- Episode recording enables learning from failures

### Negative
- In-memory backend is not persistent (production requires Redis/PostgreSQL)
- Vector search requires embedding model
- Memory lifecycle management adds complexity

### Neutral
- Pluggable backend: InMemory (dev), Redis (staging), PostgreSQL+pgvector (prod)
- Search modes: VECTOR, KEYWORD, HYBRID (default)
