"""
Distributed State Management - State machines, consensus, and distributed coordination.
"""

from .manager import (
    StateType,
    ConsistencyLevel,
    ReplicationStrategy,
    StateEntry,
    StateChange,
    StateStore,
    InMemoryStateStore,
    StateManager,
    StateMachine,
    StateMachineRegistry,
    create_state_manager,
    create_in_memory_store,
    create_state_machine,
    create_state_machine_registry,
)

__all__ = [
    "StateType",
    "ConsistencyLevel",
    "ReplicationStrategy",
    "StateEntry",
    "StateChange",
    "StateStore",
    "InMemoryStateStore",
    "StateManager",
    "StateMachine",
    "StateMachineRegistry",
    "create_state_manager",
    "create_in_memory_store",
    "create_state_machine",
    "create_state_machine_registry",
]
