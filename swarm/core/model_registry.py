"""
Model Registry - Registry with fallback chains and health monitoring
"""
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ModelStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ModelConfig:
    id: str
    provider: str
    model: str
    priority: int
    capabilities: List[str]
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = 60


@dataclass
class ModelHealth:
    model_id: str
    status: ModelStatus = ModelStatus.UNKNOWN
    last_check: float = 0
    consecutive_failures: int = 0
    last_latency: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0


class ModelRegistry:
    """Registry for models with fallback chains and health monitoring."""

    # Default model configurations matching opencode.json
    DEFAULT_MODELS = {
        "innovator": [
            ModelConfig("deepseek-v4-flash", "opencode", "opencode/deepseek-v4-flash-free", 1,
                       ["creativity", "reasoning", "coding"]),
            ModelConfig("ling-flash", "opencode", "opencode/ling-3-0-flash-free", 2,
                       ["fast_reasoning"]),
        ],
        "critic": [
            ModelConfig("nemotron-ultra", "opencode", "opencode/nemotron-3-ultra-free", 1,
                       ["security", "code_review", "analysis"]),
        ],
        "architect": [
            ModelConfig("nemotron-ultra", "opencode", "opencode/nemotron-3-ultra-free", 1,
                       ["coding", "architecture", "implementation"]),
        ],
        "explorer": [
            ModelConfig("mimo-v2-5", "opencode", "opencode/mimo-v2-5-free", 1,
                       ["research", "discovery", "web_search"]),
        ],
        "reviewer": [
            ModelConfig("nemotron-ultra", "opencode", "opencode/nemotron-3-ultra-free", 1,
                       ["ux", "design", "documentation"]),
        ],
        "reasoner": [
            ModelConfig("tencent-hy3", "opencode", "opencode/tencent-hy3-free", 1,
                       ["logic", "math", "verification"]),
        ],
        "vision-coder": [
            ModelConfig("mimo-v2-5", "opencode", "opencode/mimo-v2-5-free", 1,
                       ["vision", "multimodal", "coding"]),
        ],
        "laguna-s-2-1": [
            ModelConfig("laguna-s-2-1", "opencode", "opencode/laguna-s-2-1-free", 1,
                       ["general", "diverse_tasks"]),
        ],
        "ling-3-0-flash": [
            ModelConfig("ling-3-0-flash", "opencode", "opencode/ling-3-0-flash-free", 1,
                       ["fast_reasoning"]),
        ],
        "swarm-worker-qa": [
            ModelConfig("nemotron-ultra", "opencode", "opencode/nemotron-3-ultra-free", 1,
                       ["testing", "qa", "verification"]),
        ],
    }

    def __init__(self):
        self.models: Dict[str, List[ModelConfig]] = {}
        self.health: Dict[str, ModelHealth] = {}
        self._lock = threading.RLock()
        self.circuit_breaker_threshold = 3
        self.circuit_breaker_timeout = 600  # 10 minutes
        self._load_defaults()

    def _load_defaults(self):
        """Load default model configurations."""
        with self._lock:
            for worker, configs in self.DEFAULT_MODELS.items():
                self.models[worker] = sorted(configs, key=lambda c: c.priority)
                for config in configs:
                    key = f"{worker}:{config.id}"
                    if key not in self.health:
                        self.health[key] = ModelHealth(model_id=key)

    def get_models_for_worker(self, worker: str) -> List[ModelConfig]:
        """Get all models for a worker, sorted by priority."""
        with self._lock:
            return self.models.get(worker, []).copy()

    def get_primary_model(self, worker: str) -> Optional[ModelConfig]:
        """Get the primary (highest priority healthy) model for a worker."""
        with self._lock:
            models = self.models.get(worker, [])
            for config in models:
                if self.is_healthy(worker, config.id):
                    return config
            # Fallback to first if all unhealthy
            return models[0] if models else None

    def is_healthy(self, worker: str, model_id: str) -> bool:
        """Check if a model is healthy."""
        with self._lock:
            key = f"{worker}:{model_id}"
            health = self.health.get(key)
            if not health:
                return True  # Unknown = assume healthy
            return health.status == ModelStatus.HEALTHY

    def record_success(self, worker: str, model_id: str, latency: float):
        """Record a successful request."""
        with self._lock:
            key = f"{worker}:{model_id}"
            health = self.health.get(key)
            if health:
                health.consecutive_failures = 0
                health.last_latency = latency
                health.total_requests += 1
                health.successful_requests += 1
                health.last_check = time.time()
                health.status = ModelStatus.HEALTHY

    def record_failure(self, worker: str, model_id: str):
        """Record a failed request."""
        with self._lock:
            key = f"{worker}:{model_id}"
            health = self.health.get(key)
            if health:
                health.consecutive_failures += 1
                health.total_requests += 1
                health.last_check = time.time()

                if health.consecutive_failures >= self.circuit_breaker_threshold:
                    health.status = ModelStatus.UNHEALTHY
                elif health.consecutive_failures >= 1:
                    health.status = ModelStatus.DEGRADED

    def get_fallback_chain(self, worker: str) -> List[ModelConfig]:
        """Get ordered fallback chain for a worker."""
        with self._lock:
            models = self.models.get(worker, [])
            healthy = [m for m in models if self.is_healthy(worker, m.id)]
            unhealthy = [m for m in models if not self.is_healthy(worker, m.id)]
            return healthy + unhealthy

    def get_stats(self, worker: str) -> Dict[str, Any]:
        """Get statistics for a worker's models."""
        with self._lock:
            models = self.models.get(worker, [])
            stats = {}
            for config in models:
                key = f"{worker}:{config.id}"
                health = self.health.get(key)
                stats[config.id] = {
                    "status": health.status.value if health else "unknown",
                    "consecutive_failures": health.consecutive_failures if health else 0,
                    "success_rate": (
                        health.successful_requests / health.total_requests
                        if health and health.total_requests > 0 else 0
                    ),
                    "avg_latency": health.last_latency if health else 0,
                }
            return stats

    def start_health_monitor(self, interval: int = 300):
        """Start background health monitoring (placeholder for future implementation)."""
        pass  # Would run health checks periodically
