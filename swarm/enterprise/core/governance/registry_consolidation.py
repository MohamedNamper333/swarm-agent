"""
Model Registry Consolidation — F-019: V1/V2 Registry Duplication fix.

Unifies model_registry.py and model_registry_v2.py into single authoritative ModelRegistry
with ProviderAdapter, ModelSelectionPolicy, FallbackPolicy.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from datetime import datetime, timezone
import threading
import logging

from swarm.enterprise.core.model_registry_v2 import (
    EnterpriseModelRegistry,
    FallbackChain,
    Provider,
    EnterpriseModelConfig,
)

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Model selection strategy."""
    PRIORITY = "priority"           # Use priority order
    COST_OPTIMIZED = "cost_optimized"  # Minimize cost
    LATENCY_OPTIMIZED = "latency_optimized"  # Minimize latency
    QUALITY_OPTIMIZED = "quality_optimized"  # Maximize quality
    ROUND_ROBIN = "round_robin"     # Distribute load


class FallbackPolicyType(str, Enum):
    """Fallback policy type."""
    SEQUENTIAL = "sequential"       # Try each in order
    PARALLEL = "parallel"           # Try all simultaneously
    ADAPTIVE = "adaptive"           # Learn from failures


@dataclass(frozen=True)
class ProviderAdapter:
    """Adapter for a specific provider."""
    provider: Provider
    endpoint: str
    auth_method: str  # "api_key", "oauth", "mtls"
    auth_config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    rate_limit_rpm: int = 1000
    timeout_seconds: int = 30
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "endpoint": self.endpoint,
            "auth_method": self.auth_method,
            "capabilities": self.capabilities,
            "rate_limit_rpm": self.rate_limit_rpm,
            "timeout_seconds": self.timeout_seconds,
            "is_healthy": self.is_healthy,
        }


@dataclass(frozen=True)
class ModelSelectionPolicy:
    """Policy for selecting models."""
    strategy: SelectionStrategy = SelectionStrategy.PRIORITY
    fallback_policy: FallbackPolicyType = FallbackPolicyType.SEQUENTIAL
    max_fallbacks: int = 3
    preferred_providers: List[Provider] = field(default_factory=list)
    excluded_providers: List[Provider] = field(default_factory=list)
    cost_weight: float = 0.3
    latency_weight: float = 0.3
    quality_weight: float = 0.4
    min_quality_score: float = 0.7
    max_cost_per_1k: Optional[float] = None
    max_latency_ms: Optional[int] = None


@dataclass(frozen=True)
class FallbackPolicy:
    """Fallback behavior policy."""
    fallback_type: FallbackPolicyType = FallbackPolicyType.SEQUENTIAL
    max_retries_per_level: int = 2
    base_timeout_seconds: int = 3
    exponential_backoff: bool = True
    jitter_factor: float = 0.1
    circuit_breaker_threshold: float = 0.8
    retry_on: List[str] = field(default_factory=lambda: ["timeout", "rate_limit", "server_error"])
    stop_on: List[str] = field(default_factory=lambda: ["auth_error", "invalid_request"])


class UnifiedModelRegistry:
    """
    Unified Model Registry — consolidates V1 and V2 registries.
    
    Single authoritative source for:
    - Model catalog
    - Provider adapters
    - Fallback chains
    - Selection policies
    - Fallback policies
    """

    def __init__(self):
        self._models: Dict[str, EnterpriseModelConfig] = {}
        self._provider_adapters: Dict[Provider, ProviderAdapter] = {}
        self._fallback_chains: Dict[str, FallbackChain] = {}
        self._selection_policies: Dict[str, ModelSelectionPolicy] = {}
        self._fallback_policies: Dict[str, FallbackPolicy] = {}
        self._lock = threading.RLock()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize from V2 registry (authoritative source)."""
        with self._lock:
            if self._initialized:
                return

            # Import V2 registry as authoritative source
            v2_registry = EnterpriseModelRegistry

            # Copy models
            for model_id, config in v2_registry.MODELS.items():
                self._models[model_id] = config

            # Copy fallback chains
            for chain_id, chain in v2_registry.ALL_CHAINS.items():
                self._fallback_chains[chain_id] = chain

            # Create default provider adapters
            self._create_default_adapters()

            # Create default selection policies
            self._create_default_selection_policies()

            # Create default fallback policies
            self._create_default_fallback_policies()

            self._initialized = True
            logger.info("UnifiedModelRegistry initialized from V2 registry")

    def _create_default_adapters(self):
        """Create default provider adapters."""
        adapters = {
            Provider.NVIDIA_NIM: ProviderAdapter(
                provider=Provider.NVIDIA_NIM,
                endpoint="https://integrate.api.nvidia.com/v1",
                auth_method="api_key",
                auth_config={"header": "Authorization", "prefix": "Bearer"},
                capabilities=["chat", "completion", "embedding", "safety", "image", "video"],
                rate_limit_rpm=1000,
                timeout_seconds=30,
            ),
            Provider.OPENCODE_ZEN: ProviderAdapter(
                provider=Provider.OPENCODE_ZEN,
                endpoint="https://api.opencode.ai/v1",
                auth_method="api_key",
                capabilities=["chat", "completion"],
                rate_limit_rpm=500,
                timeout_seconds=60,
            ),
            Provider.OPENCODE: ProviderAdapter(
                provider=Provider.OPENCODE,
                endpoint="https://api.opencode.ai/v1",
                auth_method="api_key",
                capabilities=["chat", "completion"],
                rate_limit_rpm=500,
                timeout_seconds=60,
            ),
        }
        for provider, adapter in adapters.items():
            self._provider_adapters[provider] = adapter

    def _create_default_selection_policies(self):
        """Create default selection policies."""
        self._selection_policies["default"] = ModelSelectionPolicy(
            strategy=SelectionStrategy.PRIORITY,
            fallback_policy=FallbackPolicyType.SEQUENTIAL,
            max_fallbacks=3,
            cost_weight=0.3,
            latency_weight=0.3,
            quality_weight=0.4,
        )
        self._selection_policies["cost_optimized"] = ModelSelectionPolicy(
            strategy=SelectionStrategy.COST_OPTIMIZED,
            fallback_policy=FallbackPolicyType.SEQUENTIAL,
            cost_weight=0.7,
            latency_weight=0.2,
            quality_weight=0.1,
        )
        self._selection_policies["latency_optimized"] = ModelSelectionPolicy(
            strategy=SelectionStrategy.LATENCY_OPTIMIZED,
            fallback_policy=FallbackPolicyType.PARALLEL,
            latency_weight=0.7,
            cost_weight=0.2,
            quality_weight=0.1,
        )

    def _create_default_fallback_policies(self):
        """Create default fallback policies."""
        self._fallback_policies["default"] = FallbackPolicy(
            fallback_type=FallbackPolicyType.SEQUENTIAL,
            max_retries_per_level=2,
            base_timeout_seconds=3,
            exponential_backoff=True,
            jitter_factor=0.1,
            circuit_breaker_threshold=0.8,
        )
        self._fallback_policies["aggressive"] = FallbackPolicy(
            fallback_type=FallbackPolicyType.PARALLEL,
            max_retries_per_level=1,
            base_timeout_seconds=1,
            circuit_breaker_threshold=0.5,
        )
        self._fallback_policies["conservative"] = FallbackPolicy(
            fallback_type=FallbackPolicyType.SEQUENTIAL,
            max_retries_per_level=3,
            base_timeout_seconds=10,
            retry_on=["timeout", "rate_limit", "server_error", "network_error"],
        )

    # Model catalog methods
    def register_model(self, config: EnterpriseModelConfig) -> None:
        """Register a model."""
        with self._lock:
            self._models[config.id] = config

    def get_model(self, model_id: str) -> Optional[EnterpriseModelConfig]:
        """Get model by ID."""
        with self._lock:
            return self._models.get(model_id)

    def list_models(self, provider: Optional[Provider] = None) -> List[EnterpriseModelConfig]:
        """List all models, optionally filtered by provider."""
        with self._lock:
            models = list(self._models.values())
            if provider:
                models = [m for m in models if m.provider == provider]
            return models

    # Provider adapter methods
    def register_provider_adapter(self, adapter: ProviderAdapter) -> None:
        """Register a provider adapter."""
        with self._lock:
            self._provider_adapters[adapter.provider] = adapter

    def get_provider_adapter(self, provider: Provider) -> Optional[ProviderAdapter]:
        """Get provider adapter."""
        with self._lock:
            return self._provider_adapters.get(provider)

    # Fallback chain methods
    def register_fallback_chain(self, chain: FallbackChain) -> None:
        """Register a fallback chain."""
        with self._lock:
            self._fallback_chains[chain.role] = chain

    def get_fallback_chain(self, role: str) -> Optional[FallbackChain]:
        """Get fallback chain for role."""
        with self._lock:
            return self._fallback_chains.get(role)

    def get_all_chains(self) -> Dict[str, FallbackChain]:
        """Get all fallback chains."""
        with self._lock:
            return dict(self._fallback_chains)

    # Selection policy methods
    def set_selection_policy(self, name: str, policy: ModelSelectionPolicy) -> None:
        """Set selection policy."""
        with self._lock:
            self._selection_policies[name] = policy

    def get_selection_policy(self, name: str = "default") -> ModelSelectionPolicy:
        """Get selection policy."""
        with self._lock:
            return self._selection_policies.get(name, self._selection_policies["default"])

    # Fallback policy methods
    def set_fallback_policy(self, name: str, policy: FallbackPolicy) -> None:
        """Set fallback policy."""
        with self._lock:
            self._fallback_policies[name] = policy

    def get_fallback_policy(self, name: str = "default") -> FallbackPolicy:
        """Get fallback policy."""
        with self._lock:
            return self._fallback_policies.get(name, self._fallback_policies["default"])

    # Migration from V1
    def migrate_from_v1(self, v1_registry) -> Dict[str, int]:
        """
        Migrate from V1 model registry.
        Returns migration statistics.
        """
        stats = {"models_migrated": 0, "chains_migrated": 0, "conflicts": 0}

        with self._lock:
            # V1 uses different structure - migrate models
            if hasattr(v1_registry, 'models'):
                for worker, configs in v1_registry.models.items():
                    for config in configs:
                        model_id = f"{worker}:{config.id}"
                        if model_id not in self._models:
                            # Convert V1 config to EnterpriseModelConfig
                            enterprise_config = EnterpriseModelConfig(
                                id=model_id,
                                provider=Provider.OPENCODE,
                                model=config.model,
                                priority=config.priority,
                                capabilities=config.capabilities,
                                max_tokens=config.max_tokens,
                                temperature=config.temperature,
                                timeout=config.timeout,
                            )
                            self._models[model_id] = enterprise_config
                            stats["models_migrated"] += 1
                        else:
                            stats["conflicts"] += 1

        logger.info(f"V1 migration complete: {stats}")
        return stats

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "models": len(self._models),
                "provider_adapters": len(self._provider_adapters),
                "fallback_chains": len(self._fallback_chains),
                "selection_policies": list(self._selection_policies.keys()),
                "fallback_policies": list(self._fallback_policies.keys()),
                "models_by_provider": {
                    p.value: len([m for m in self._models.values() if m.provider == p])
                    for p in Provider
                },
            }


# Migration helper
def consolidate_registries(v1_registry, v2_registry: EnterpriseModelRegistry) -> UnifiedModelRegistry:
    """
    Consolidate V1 and V2 registries into unified registry.
    V2 is authoritative; V1 supplements for missing models.
    """
    unified = UnifiedModelRegistry()
    unified.initialize()

    # Migrate any missing models from V1
    unified.migrate_from_v1(v1_registry)

    return unified


# Global unified registry
_unified_registry: Optional[UnifiedModelRegistry] = None
_ur_lock = threading.Lock()


def get_unified_model_registry() -> UnifiedModelRegistry:
    global _unified_registry
    with _ur_lock:
        if _unified_registry is None:
            _unified_registry = UnifiedModelRegistry()
            _unified_registry.initialize()
        return _unified_registry


__all__ = [
    "SelectionStrategy",
    "FallbackPolicyType",
    "ProviderAdapter",
    "ModelSelectionPolicy",
    "FallbackPolicy",
    "UnifiedModelRegistry",
    "consolidate_registries",
    "get_unified_model_registry",
]