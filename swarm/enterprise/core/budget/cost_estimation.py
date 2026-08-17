"""
Cost Estimation Service — server-authoritative cost calculation.

F-002: Client-Controlled Cost fix.
Removes `estimated_cost` from client requests; computes cost server-side.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import threading


class CostComponent(str, Enum):
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    TOOL_CALLS = "tool_calls"
    MEDIA_UNITS = "media_units"
    DURATION_SECONDS = "duration_seconds"
    EXTERNAL_CHARGES = "external_charges"


@dataclass(frozen=True)
class PricingModel:
    """Pricing for a specific provider/model combination."""
    provider: str
    model: str
    input_token_price_per_1k: Decimal = Decimal("0")
    output_token_price_per_1k: Decimal = Decimal("0")
    tool_call_price: Decimal = Decimal("0")
    media_unit_price: Decimal = Decimal("0")
    duration_price_per_second: Decimal = Decimal("0")
    currency: str = "USD"
    pricing_version: str = "1.0"
    effective_date: str = ""


# Default pricing for free tier NVIDIA NIM (all $0)
DEFAULT_FREE_PRICING = PricingModel(
    provider="nvidia_nim",
    model="*",
    input_token_price_per_1k=Decimal("0"),
    output_token_price_per_1k=Decimal("0"),
    tool_call_price=Decimal("0"),
    media_unit_price=Decimal("0"),
    duration_price_per_second=Decimal("0"),
)


@dataclass(frozen=True)
class CostEstimate:
    """Complete cost estimate for an execution."""
    components: Dict[CostComponent, Decimal]
    total: Decimal
    currency: str
    pricing_version: str
    breakdown: Dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure total matches sum of components
        calculated = sum(self.components.values(), Decimal("0"))
        if calculated != self.total:
            object.__setattr__(self, "total", calculated)


@dataclass
class CostEstimationRequest:
    """Request for cost estimation."""
    provider: str
    model: str
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    estimated_tool_calls: int = 0
    estimated_media_units: int = 0
    estimated_duration_seconds: int = 0
    external_charges: Decimal = Decimal("0")
    tenant_id: str = "default"


class CostEstimationService:
    """Server-authoritative cost estimation."""

    def __init__(self):
        self._pricing: Dict[str, PricingModel] = {}
        self._lock = threading.RLock()
        self._register_default_pricing()

    def _register_default_pricing(self):
        """Register default free-tier pricing."""
        # All NVIDIA NIM models on free tier
        free_models = [
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-nano-30b-a3b",
            "nvidia/nemotron-mini-4b-instruct",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/nemotron-content-safety-reasoning-4b",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control",
            "nvidia/nemoguard-jailbreak-detect",
            "nvidia/riva-translate-4b-instruct-v1.1",
            "nvidia/riva-translate-4b-instruct-v2",
            "nvidia/llama-3.2-nv-embedqa-1b-v2",
            "nvidia/llama-3.2-nemoretriever-300m-embed-v2",
            "deepseek-ai/deepseek-v4-pro",
            "deepseek-ai/deepseek-v4-flash",
            "moonshotai/kimi-k2.5",
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.2-11b-vision-instruct",
            "qwen/qwen2.5-coder-32b-instruct",
            "qwen/qwen3-coder-480b-a35b-instruct",
            "black-forest-labs/flux.1-dev",
            "stabilityai/stable-video-diffusion",
            "minimaxai/minimax-m3",
        ]
        for model in free_models:
            self._pricing[model] = PricingModel(
                provider="nvidia_nim",
                model=model,
                input_token_price_per_1k=Decimal("0"),
                output_token_price_per_1k=Decimal("0"),
                tool_call_price=Decimal("0"),
                media_unit_price=Decimal("0"),
                duration_price_per_second=Decimal("0"),
            )

    def register_pricing(self, model: str, pricing: PricingModel) -> None:
        """Register custom pricing for a model."""
        with self._lock:
            self._pricing[model] = pricing

    def get_pricing(self, model: str) -> PricingModel:
        """Get pricing for a model (falls back to free tier)."""
        with self._lock:
            return self._pricing.get(model, DEFAULT_FREE_PRICING)

    def estimate(self, request: CostEstimationRequest) -> CostEstimate:
        """Compute authoritative cost estimate."""
        pricing = self.get_pricing(request.model)

        components = {
            CostComponent.INPUT_TOKENS: (
                Decimal(request.estimated_input_tokens) / Decimal("1000")
            ) * pricing.input_token_price_per_1k,
            CostComponent.OUTPUT_TOKENS: (
                Decimal(request.estimated_output_tokens) / Decimal("1000")
            ) * pricing.output_token_price_per_1k,
            CostComponent.TOOL_CALLS: Decimal(request.estimated_tool_calls) * pricing.tool_call_price,
            CostComponent.MEDIA_UNITS: Decimal(request.estimated_media_units) * pricing.media_unit_price,
            CostComponent.DURATION_SECONDS: Decimal(request.estimated_duration_seconds) * pricing.duration_price_per_second,
            CostComponent.EXTERNAL_CHARGES: request.external_charges,
        }

        # Quantize to 2 decimal places for currency
        quantized = {
            k: v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for k, v in components.items()
        }

        total = sum(quantized.values(), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return CostEstimate(
            components=quantized,
            total=total,
            currency=pricing.currency,
            pricing_version=pricing.pricing_version,
            breakdown={k.value: v for k, v in quantized.items()},
        )

    def estimate_from_execution(
        self,
        provider: str,
        model: str,
        actual_input_tokens: int,
        actual_output_tokens: int,
        actual_tool_calls: int,
        actual_media_units: int = 0,
        actual_duration_seconds: int = 0,
        external_charges: Decimal = Decimal("0"),
    ) -> CostEstimate:
        """Compute actual cost from execution metrics."""
        request = CostEstimationRequest(
            provider=provider,
            model=model,
            estimated_input_tokens=actual_input_tokens,
            estimated_output_tokens=actual_output_tokens,
            estimated_tool_calls=actual_tool_calls,
            estimated_media_units=actual_media_units,
            estimated_duration_seconds=actual_duration_seconds,
            external_charges=external_charges,
        )
        return self.estimate(request)


# Singleton
_cost_estimation_service: Optional[CostEstimationService] = None
_service_lock = threading.Lock()


def get_cost_estimation_service() -> CostEstimationService:
    global _cost_estimation_service
    with _service_lock:
        if _cost_estimation_service is None:
            _cost_estimation_service = CostEstimationService()
        return _cost_estimation_service


__all__ = [
    "CostComponent",
    "PricingModel",
    "CostEstimate",
    "CostEstimationRequest",
    "CostEstimationService",
    "DEFAULT_FREE_PRICING",
    "get_cost_estimation_service",
]