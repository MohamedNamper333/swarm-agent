"""
Distributed State Management — F-012: Process-Local Global Infrastructure State fix.

Ensures safety/budget/rate-limit state is authoritative and consistent across horizontal scaling.
Decides per state type: process-local (non-authoritative) vs distributed (authoritative).
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, Callable
from enum import Enum
from datetime import datetime, timezone
import threading
import logging

logger = logging.getLogger(__name__)


class StateScope(str, Enum):
    """Scope of state: where it's authoritative."""
    PROCESS_LOCAL = "process_local"      # Non-authoritative, per-process cache
    DISTRIBUTED = "distributed"           # Authoritative, shared across processes
    TENANT_LOCAL = "tenant_local"         # Per-tenant authoritative


class StateType(str, Enum):
    """Types of infrastructure state."""
    BUDGET = "budget"                     # Authoritative: DISTRIBUTED
    RATE_LIMIT = "rate_limit"             # Authoritative: DISTRIBUTED
    SAFETY = "safety"                     # Authoritative: DISTRIBUTED
    CIRCUIT_BREAKER = "circuit_breaker"   # Authoritative: DISTRIBUTED
    CACHE = "cache"                       # Non-authoritative: PROCESS_LOCAL
    METRICS = "metrics"                   # Non-authoritative: PROCESS_LOCAL (aggregated)


@dataclass(frozen=True)
class StateDescriptor:
    """Describes a piece of infrastructure state."""
    name: str
    state_type: StateType
    scope: StateScope
    ttl_seconds: Optional[int] = None
    description: str = ""


class DistributedStateBackend:
    """Abstract backend for distributed state."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def compare_and_swap(self, key: str, expected: Any, new_value: Any) -> bool:
        raise NotImplementedError

    def increment(self, key: str, delta: int = 1) -> int:
        raise NotImplementedError


class InMemoryDistributedBackend(DistributedStateBackend):
    """In-memory distributed backend (for single-process or testing)."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            self._data[key] = value
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def compare_and_swap(self, key: str, expected: Any, new_value: Any) -> bool:
        with self._lock:
            if self._data.get(key) == expected:
                self._data[key] = new_value
                return True
            return False

    def increment(self, key: str, delta: int = 1) -> int:
        with self._lock:
            current = self._data.get(key, 0)
            new_val = current + delta
            self._data[key] = new_val
            return new_val


class RedisDistributedBackend(DistributedStateBackend):
    """Redis-backed distributed state (production)."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def get(self, key: str) -> Optional[Any]:
        import json
        val = self._redis.get(key)
        return json.loads(val) if val else None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import json
        return self._redis.set(key, json.dumps(value), ex=ttl)

    def delete(self, key: str) -> bool:
        return self._redis.delete(key) > 0

    def compare_and_swap(self, key: str, expected: Any, new_value: Any) -> bool:
        import json
        # Use Lua script for atomic CAS
        lua_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            redis.call('SET', KEYS[1], ARGV[2])
            return 1
        else
            return 0
        end
        """
        return self._redis.eval(lua_script, 1, key, json.dumps(expected), json.dumps(new_value)) == 1

    def increment(self, key: str, delta: int = 1) -> int:
        return self._redis.incrby(key, delta)


class StateManager:
    """
    Manages infrastructure state with correct scope and backend.
    
    Decision matrix:
    - BUDGET, RATE_LIMIT, SAFETY, CIRCUIT_BREAKER → DISTRIBUTED (authoritative)
    - CACHE, METRICS → PROCESS_LOCAL (non-authoritative)
    """

    DEFAULT_DESCRIPTORS = {
        "budget": StateDescriptor("budget", StateType.BUDGET, StateScope.DISTRIBUTED, description="Budget reservations and consumption"),
        "rate_limit": StateDescriptor("rate_limit", StateType.RATE_LIMIT, StateScope.DISTRIBUTED, description="Rate limit counters"),
        "safety": StateDescriptor("safety", StateType.SAFETY, StateScope.DISTRIBUTED, description="Safety decisions and vetoes"),
        "circuit_breaker": StateDescriptor("circuit_breaker", StateType.CIRCUIT_BREAKER, StateScope.DISTRIBUTED, description="Circuit breaker states"),
        "cache": StateDescriptor("cache", StateType.CACHE, StateScope.PROCESS_LOCAL, ttl_seconds=3600, description="Response cache"),
        "metrics": StateDescriptor("metrics", StateType.METRICS, StateScope.PROCESS_LOCAL, description="Aggregated metrics"),
    }

    def __init__(self, distributed_backend: Optional[DistributedStateBackend] = None):
        self._descriptors = dict(self.DEFAULT_DESCRIPTORS)
        self._distributed = distributed_backend or InMemoryDistributedBackend()
        self._local: Dict[str, Any] = {}
        self._local_lock = threading.RLock()

    def register_descriptor(self, descriptor: StateDescriptor) -> None:
        """Register a custom state descriptor."""
        self._descriptors[descriptor.name] = descriptor

    def get(self, name: str, key: str) -> Optional[Any]:
        """Get state value."""
        descriptor = self._descriptors.get(name)
        if not descriptor:
            raise ValueError(f"Unknown state: {name}")

        full_key = f"{name}:{key}"
        if descriptor.scope == StateScope.DISTRIBUTED:
            return self._distributed.get(full_key)
        else:
            with self._local_lock:
                return self._local.get(full_key)

    def set(self, name: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set state value."""
        descriptor = self._descriptors.get(name)
        if not descriptor:
            raise ValueError(f"Unknown state: {name}")

        full_key = f"{name}:{key}"
        effective_ttl = ttl or descriptor.ttl_seconds

        if descriptor.scope == StateScope.DISTRIBUTED:
            return self._distributed.set(full_key, value, effective_ttl)
        else:
            with self._local_lock:
                self._local[full_key] = value
                return True

    def compare_and_swap(self, name: str, key: str, expected: Any, new_value: Any) -> bool:
        """Atomic compare-and-swap (only for distributed state)."""
        descriptor = self._descriptors.get(name)
        if not descriptor:
            raise ValueError(f"Unknown state: {name}")
        if descriptor.scope != StateScope.DISTRIBUTED:
            raise ValueError(f"CAS only supported for distributed state: {name}")

        full_key = f"{name}:{key}"
        return self._distributed.compare_and_swap(full_key, expected, new_value)

    def increment(self, name: str, key: str, delta: int = 1) -> int:
        """Atomic increment (only for distributed state)."""
        descriptor = self._descriptors.get(name)
        if not descriptor:
            raise ValueError(f"Unknown state: {name}")
        if descriptor.scope != StateScope.DISTRIBUTED:
            raise ValueError(f"Increment only supported for distributed state: {name}")

        full_key = f"{name}:{key}"
        return self._distributed.increment(full_key, delta)

    def delete(self, name: str, key: str) -> bool:
        """Delete state."""
        descriptor = self._descriptors.get(name)
        if not descriptor:
            raise ValueError(f"Unknown state: {name}")

        full_key = f"{name}:{key}"
        if descriptor.scope == StateScope.DISTRIBUTED:
            return self._distributed.delete(full_key)
        else:
            with self._local_lock:
                if full_key in self._local:
                    del self._local[full_key]
                    return True
                return False

    def get_descriptor(self, name: str) -> Optional[StateDescriptor]:
        """Get state descriptor."""
        return self._descriptors.get(name)

    def list_descriptors(self) -> Dict[str, StateDescriptor]:
        """List all descriptors."""
        return dict(self._descriptors)


# Global state manager
_state_manager: Optional[StateManager] = None
_sm_lock = threading.Lock()


def get_state_manager() -> StateManager:
    global _state_manager
    with _sm_lock:
        if _state_manager is None:
            _state_manager = StateManager()
        return _state_manager


def set_distributed_backend(backend: DistributedStateBackend) -> None:
    """Set distributed backend (call once at startup)."""
    global _state_manager
    with _sm_lock:
        _state_manager = StateManager(distributed_backend=backend)


__all__ = [
    "StateScope",
    "StateType",
    "StateDescriptor",
    "DistributedStateBackend",
    "InMemoryDistributedBackend",
    "RedisDistributedBackend",
    "StateManager",
    "get_state_manager",
    "set_distributed_backend",
]