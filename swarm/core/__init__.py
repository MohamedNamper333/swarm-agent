"""
Swarm Core - Dynamic Core Module
The heart of the Swarm Agent System.
"""

from .agent_router import AgentRouter
from .model_registry import ModelRegistry
from .task_dag import DAGBuilder, DAG
from .task_classifier import TaskClassifier
from .inter_agent_bus import AgentBus
from .agent_state_machine import AgentStateMachine, AgentState
from .auto_verdict import AutoVerdictEngine
from .memory_engine import MemoryEngine
from .config_loader import ConfigLoader

__all__ = [
    "AgentRouter",
    "ModelRegistry",
    "DAGBuilder",
    "DAG",
    "TaskClassifier",
    "AgentBus",
    "AgentStateMachine",
    "AgentState",
    "AutoVerdictEngine",
    "MemoryEngine",
    "ConfigLoader",
]

__version__ = "3.0.0"
