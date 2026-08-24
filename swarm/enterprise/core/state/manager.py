"""
Distributed State Management - State machines, consensus, and distributed coordination.
"""

import asyncio
import threading
import time
import uuid
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# State Models
# =============================================================================

class StateType(str, Enum):
    KEY_VALUE = "key_value"
    COUNTER = "counter"
    SET = "set"
    MAP = "map"
    SEQUENCE = "sequence"
    LOCK = "lock"
    SESSION = "session"
    WORKFLOW = "workflow"
    AGENT = "agent"


class ConsistencyLevel(str, Enum):
    EVENTUAL = "eventual"
    STRONG = "strong"
    SEQUENTIAL = "sequential"
    CAUSAL = "causal"


class ReplicationStrategy(str, Enum):
    LEADER_FOLLOWER = "leader_follower"
    MULTI_LEADER = "multi_leader"
    LEADERLESS = "leaderless"
    RAFT = "raft"


@dataclass
class StateEntry:
    key: str = ""
    value: Any = None
    version: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.now(timezone.utc) > self.expires_at
        return False


@dataclass
class StateChange:
    change_id: str = field(default_factory=lambda: f"chg-{uuidv7()}")
    key: str = ""
    old_value: Any = None
    new_value: Any = None
    operation: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str = "system"
    trace_id: Optional[str] = None


# =============================================================================
# State Store Interface
# =============================================================================

class StateStore(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[StateEntry]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> StateEntry:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        pass
    
    @abstractmethod
    def increment(self, key: str, delta: int = 1) -> int:
        pass
    
    @abstractmethod
    def compare_and_set(self, key: str, expected: Any, new_value: Any) -> bool:
        pass
    
    @abstractmethod
    def get_multi(self, keys: List[str]) -> Dict[str, StateEntry]:
        pass
    
    @abstractmethod
    def set_multi(self, entries: Dict[str, Any]) -> Dict[str, StateEntry]:
        pass


# =============================================================================
# In-Memory State Store
# =============================================================================

class InMemoryStateStore(StateStore):
    def __init__(self):
        self._data: Dict[str, StateEntry] = {}
        self._lock = threading.RLock()
        self._cleanup_running = False
        self._cleanup_thread: Optional[threading.Thread] = None
    
    def get(self, key: str) -> Optional[StateEntry]:
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.is_expired():
                del self._data[key]
                return None
            return entry
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> StateEntry:
        with self._lock:
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            
            entry = StateEntry(
                key=key,
                value=value,
                timestamp=now_utc(),
                expires_at=expires_at,
            )
            self._data[key] = entry
            return entry
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.is_expired():
                del self._data[key]
                return False
            return key in self._data
    
    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            import fnmatch
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def increment(self, key: str, delta: int = 1) -> int:
        with self._lock:
            entry = self._data.get(key)
            if entry:
                if isinstance(entry.value, (int, float)):
                    entry.value += delta
                    entry.version += 1
                    entry.timestamp = now_utc()
                    return entry.value
                else:
                    raise ValueError("Cannot increment non-numeric value")
            else:
                entry = StateEntry(key=key, value=delta)
                self._data[key] = entry
                return delta
    
    def compare_and_set(self, key: str, expected: Any, new_value: Any) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.value == expected:
                entry.value = new_value
                entry.version += 1
                entry.timestamp = now_utc()
                return True
            return False
    
    def get_multi(self, keys: List[str]) -> Dict[str, StateEntry]:
        with self._lock:
            result = {}
            for key in keys:
                entry = self._data.get(key)
                if entry and not entry.is_expired():
                    result[key] = entry
            return result
    
    def set_multi(self, entries: Dict[str, Any]) -> Dict[str, StateEntry]:
        with self._lock:
            result = {}
            for key, value in entries.items():
                entry = StateEntry(key=key, value=value, timestamp=now_utc())
                self._data[key] = entry
                result[key] = entry
            return result
    
    def start_cleanup(self, interval: int = 60) -> None:
        if self._cleanup_running:
            return
        
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, args=(interval,), daemon=True)
        self._cleanup_thread.start()
    
    def stop_cleanup(self) -> None:
        self._cleanup_running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
    
    def _cleanup_loop(self, interval: int) -> None:
        while self._cleanup_running:
            time.sleep(interval)
            with self._lock:
                expired = [k for k, v in self._data.items() if v.is_expired()]
                for k in expired:
                    del self._data[k]


# =============================================================================
# Distributed State Manager
# =============================================================================

class StateManager:
    def __init__(
        self,
        store: Optional[StateStore] = None,
        default_ttl_seconds: Optional[int] = None,
    ):
        self.store = store or InMemoryStateStore()
        self.default_ttl = default_ttl_seconds
        self._lock = threading.RLock()
        
        self._listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = defaultdict(list)
        self._global_listeners: List[Callable[[str, Any, Any], None]] = []
        
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._tx_lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        entry = self.store.get(key)
        return entry.value if entry else None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        actor_id: str = "system",
    ) -> bool:
        ttl = ttl_seconds or self.default_ttl
        entry = self.store.set(key, value, ttl)
        
        self._notify(key, None, value, actor_id)
        return True
    
    def delete(self, key: str, actor_id: str = "system") -> bool:
        old = self.get(key)
        result = self.store.delete(key)
        if result:
            self._notify(key, old, None, actor_id)
        return result
    
    def exists(self, key: str) -> bool:
        return self.store.exists(key)
    
    def increment(self, key: str, delta: int = 1) -> int:
        return self.store.increment(key, delta)
    
    def compare_and_set(self, key: str, expected: Any, new_value: Any) -> bool:
        return self.store.compare_and_set(key, expected, new_value)
    
    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        entries = self.store.get_multi(keys)
        return {k: v.value for k, v in entries.items()}
    
    def set_multi(self, entries: Dict[str, Any]) -> Dict[str, Any]:
        entries_obj = self.store.set_multi(entries)
        for key, entry in entries_obj.items():
            self._notify(key, None, entry.value, "system")
        return {k: v.value for k, v in entries_obj.items()}
    
    def keys(self, pattern: str = "*") -> List[str]:
        return self.store.keys(pattern)
    
    def list_append(self, key: str, value: Any) -> List[Any]:
        current = self.get(key) or []
        current.append(value)
        self.set(key, current)
        return current
    
    def list_remove(self, key: str, value: Any) -> bool:
        current = self.get(key) or []
        if value in current:
            current.remove(value)
            self.set(key, current)
            return True
        return False
    
    def list_get(self, key: str) -> List[Any]:
        return self.get(key) or []
    
    def set_add(self, key: str, value: Any) -> Set[Any]:
        current = set(self.get(key) or [])
        current.add(value)
        self.set(key, list(current))
        return current
    
    def set_remove(self, key: str, value: Any) -> bool:
        current = set(self.get(key) or [])
        if value in current:
            current.remove(value)
            self.set(key, list(current))
            return True
        return False
    
    def set_get(self, key: str) -> Set[Any]:
        return set(self.get(key) or [])
    
    def map_put(self, map_key: str, field: str, value: Any) -> Dict[str, Any]:
        current = self.get(map_key) or {}
        current[field] = value
        self.set(map_key, current)
        return current
    
    def map_get(self, map_key: str, field: str) -> Optional[Any]:
        current = self.get(map_key) or {}
        return current.get(field)
    
    def map_delete(self, map_key: str, field: str) -> bool:
        current = self.get(map_key) or {}
        if field in current:
            del current[field]
            self.set(map_key, current)
            return True
        return False
    
    def map_get_all(self, map_key: str) -> Dict[str, Any]:
        return self.get(map_key) or {}
    
    def acquire_lock(
        self,
        lock_key: str,
        owner: str,
        ttl_seconds: int = 30,
        timeout: float = 10.0,
    ) -> bool:
        lock_key = f"lock:{lock_key}"
        start = time.time()
        
        while time.time() - start < timeout:
            if self.store.compare_and_set(f"{lock_key}:owner", None, owner):
                self.store.set(f"{lock_key}:owner", owner, ttl_seconds)
                return True
            time.sleep(0.1)
        
        return False
    
    def release_lock(self, lock_key: str, owner: str) -> bool:
        return self.store.compare_and_set(f"lock:{lock_key}:owner", owner, None)
    
    def is_locked(self, lock_key: str) -> bool:
        return self.store.exists(f"lock:{lock_key}:owner")
    
    def begin_transaction(self, tx_id: Optional[str] = None) -> str:
        tx_id = tx_id or f"tx-{uuidv7()}"
        with self._tx_lock:
            self._transactions[tx_id] = {
                "operations": [],
                "started_at": now_utc(),
                "committed": False,
                "rolled_back": False,
            }
        return tx_id
    
    def tx_set(self, tx_id: str, key: str, value: Any) -> bool:
        with self._tx_lock:
            tx = self._transactions.get(tx_id)
            if not tx or tx["committed"] or tx["rolled_back"]:
                return False
            tx["operations"].append(("set", key, value))
            return True
    
    def tx_delete(self, tx_id: str, key: str) -> bool:
        with self._tx_lock:
            tx = self._transactions.get(tx_id)
            if not tx or tx["committed"] or tx["rolled_back"]:
                return False
            tx["operations"].append(("delete", key, None))
            return True
    
    def commit_transaction(self, tx_id: str) -> bool:
        with self._tx_lock:
            tx = self._transactions.get(tx_id)
            if not tx or tx["committed"] or tx["rolled_back"]:
                return False
            
            for op, key, value in tx["operations"]:
                if op == "set":
                    self.set(key, value)
                elif op == "delete":
                    self.delete(key)
            
            tx["committed"] = True
            del self._transactions[tx_id]
            return True
    
    def rollback_transaction(self, tx_id: str) -> bool:
        with self._tx_lock:
            tx = self._transactions.get(tx_id)
            if not tx or tx["committed"] or tx["rolled_back"]:
                return False
            tx["rolled_back"] = True
            del self._transactions[tx_id]
            return True
    
    def add_listener(self, key_pattern: str, callback: Callable[[str, Any, Any], None]) -> None:
        self._listeners[key_pattern].append(callback)
    
    def add_global_listener(self, callback: Callable[[str, Any, Any], None]) -> None:
        self._global_listeners.append(callback)
    
    def _notify(self, key: str, old_value: Any, new_value: Any, actor_id: str) -> None:
        import fnmatch
        
        for pattern, callbacks in self._listeners.items():
            if fnmatch.fnmatch(key, pattern):
                for cb in callbacks:
                    try:
                        cb(key, new_value, old_value)
                    except Exception as e:
                        logger.error(f"Listener error: {e}")
        
        for cb in self._global_listeners:
            try:
                cb(key, new_value, old_value)
            except Exception as e:
                logger.error(f"Global listener error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            keys = self.store.keys()
            return {
                "total_keys": len(keys),
                "listeners": sum(len(cbs) for cbs in self._listeners.values()),
                "transactions": len(self._transactions),
            }


# =============================================================================
# State Machine
# =============================================================================

class StateMachine:
    def __init__(self, entity_id: str, initial_state: str, transitions: Dict[str, List[str]]):
        self.entity_id = entity_id
        self.current_state = initial_state
        self.transitions = transitions
        self.history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        
        self.history.append({
            "state": initial_state,
            "timestamp": now_utc(),
            "trigger": "initial",
        })
    
    def can_transition(self, to_state: str) -> bool:
        with self._lock:
            return to_state in self.transitions.get(self.current_state, [])
    
    def transition(self, to_state: str, trigger: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            if not self.can_transition(to_state):
                return False
            
            old_state = self.current_state
            self.current_state = to_state
            
            self.history.append({
                "from_state": old_state,
                "to_state": to_state,
                "trigger": trigger,
                "timestamp": now_utc(),
                "metadata": metadata or {},
            })
            
            logger.info(f"State transition: {old_state} -> {to_state} (trigger: {trigger})")
            return True
    
    def get_state(self) -> str:
        with self._lock:
            return self.current_state
    
    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.history)
    
    def can_reach(self, target_state: str) -> bool:
        visited = set()
        queue = [self.current_state]
        
        while queue:
            state = queue.pop(0)
            if state == target_state:
                return True
            if state in visited:
                continue
            visited.add(state)
            queue.extend(self.transitions.get(state, []))
        
        return False


class StateMachineRegistry:
    def __init__(self):
        self._machines: Dict[str, StateMachine] = {}
        self._lock = threading.RLock()
    
    def register(
        self,
        entity_id: str,
        initial_state: str,
        transitions: Dict[str, List[str]],
    ) -> StateMachine:
        with self._lock:
            if entity_id in self._machines:
                raise ValueError(f"State machine {entity_id} already exists")
            
            machine = StateMachine(entity_id, initial_state, transitions)
            self._machines[entity_id] = machine
            return machine
    
    def get(self, entity_id: str) -> Optional[StateMachine]:
        with self._lock:
            return self._machines.get(entity_id)
    
    def unregister(self, entity_id: str) -> bool:
        with self._lock:
            if entity_id in self._machines:
                del self._machines[entity_id]
                return True
            return False
    
    def list_entities(self) -> List[str]:
        with self._lock:
            return list(self._machines.keys())


# =============================================================================
# Factory
# =============================================================================

def create_state_manager(store: Optional[StateStore] = None) -> StateManager:
    return StateManager(store)


def create_in_memory_store() -> InMemoryStateStore:
    return InMemoryStateStore()


def create_state_machine(
    entity_id: str,
    initial_state: str,
    transitions: Dict[str, List[str]],
) -> StateMachine:
    return StateMachine(entity_id, initial_state, transitions)


def create_state_machine_registry() -> StateMachineRegistry:
    return StateMachineRegistry()
