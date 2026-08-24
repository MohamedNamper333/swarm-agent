# ADR-005: Agent Registry + Task Dispatcher

## Status
**Accepted** — 2025-08-24

## Context
Departments (code, design, video, research, data, language, knowledge, safety) need to be registered as agents with capabilities. Tasks must be dispatched to the most appropriate agent based on load, capability, and health.

## Decision
Implement a service mesh pattern for agent management:

1. **AgentRegistry**: Central registry of agent types, instances, and capabilities
2. **TaskDispatcher**: Dispatches tasks using configurable strategies
3. **Circuit Breaker**: Prevents cascading failures when agents are unhealthy

### Dispatch Strategies
- `LEAST_LOADED`: Route to agent with lowest current load (default)
- `ROUND_ROBIN`: Distribute evenly across all healthy agents
- `CAPABILITY_MATCH`: Match task capability to agent capabilities
- `AFFINITY`: Route to same agent for related tasks (session affinity)

### Implementation Files
- `core/orchestration/agent_registry.py` — AgentRegistry, AgentInstance, AgentCapability
- `core/orchestration/task_dispatcher.py` — TaskDispatcher, DispatchConfig, CircuitBreaker

## Consequences

### Positive
- Dynamic agent registration/deregistration without downtime
- Health-aware routing prevents sending tasks to unhealthy agents
- Circuit breaker prevents cascading failures
- Load balancing maximizes throughput

### Negative
- Registry is an in-process singleton (not distributed)
- Heartbeat mechanism adds slight overhead
- Circuit breaker can cause temporary unavailability during recovery

### Neutral
- Agents register themselves at startup via `SwarmMaster._register_departments_as_agents()`
- Custom agents can be added via `SwarmMaster.register_agent()` API
