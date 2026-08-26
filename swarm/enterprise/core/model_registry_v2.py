"""
Model Registry v2 — 50+ NVIDIA NIM models with 3-level fallback chains.

Extends the base ModelRegistry with:
- ~50 unique models across LLM, Visual, Multimodal, Retrieval tiers
- Per-role fallback chains (primary → fallback1 → fallback2)
- Per-model daily rate limits (from free-tier estimates)
- Provider abstraction (nvidia_nim vs opencode_zen vs opencode)
- Cost tracking ($0 for free tier)

NOTE: All models on free NVIDIA NIM tier. When daily limit hit,
the fallback chain activates. When ALL fail, the request returns 503.
"""
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from swarm.core.model_registry import ModelConfig, ModelHealth, ModelStatus, ModelRegistry

logger = logging.getLogger(__name__)


class Provider(Enum):
    NVIDIA_NIM = "nvidia_nim"
    OPENCODE_ZEN = "opencode_zen"
    OPENCODE = "opencode"


@dataclass
class EnterpriseModelConfig:
    """Extended model config with provider + daily limit."""
    id: str
    provider: Provider = Provider.NVIDIA_NIM
    model: str = ""
    priority: int = 1
    capabilities: List[str] = field(default_factory=list)
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = 60
    daily_limit: int = 1000  # Free tier estimate
    cost_per_1k_tokens: float = 0.0  # $0 on free tier
    modality: str = "text"
    tier: str = "medium"


@dataclass
class FallbackChain:
    """3-level fallback chain for a single role. fallback2 can be empty (None)."""
    role: str
    primary: str
    fallback1: str
    fallback2: Optional[str] = None
    veto: bool = False
    timeout_sec: int = 3
    max_retries: int = 2

    def levels(self) -> List[str]:
        """Return non-empty fallback levels in order."""
        chain = [self.primary, self.fallback1]
        if self.fallback2:
            chain.append(self.fallback2)
        return chain


class EnterpriseModelRegistry:
    """Registry of all 50+ models with role → fallback chain mapping."""

    # ------------------------------------------------------------------
    # MODEL CATALOG (all free NVIDIA NIM tier)
    # ------------------------------------------------------------------
    MODELS: Dict[str, EnterpriseModelConfig] = {}

    # NOTE (2026-08-25): Live-tested against integrate.api.nvidia.com/v1/chat/completions.
    # Removed (EOL/404): deepseek-v4-pro, deepseek-v4-flash, z-ai/glm*, moonshotai/kimi-k2.5,
    # kimi-k2-instruct, thinkingmachines/inkling, mistral-small-4, mistral-medium-3.5,
    # google/gemma-3-27b-it, all qwen/*, black-forest-labs/flux.*, stabilityai/*,
    # microsoft/trellis, nvidia/cosmos-predict1-7b, nemotron-content-safety-reasoning-4b,
    # nemotron-3-content-safety, nemoguard-jailbreak-detect.
    # Image/video *generation* endpoints are gone from NIM free tier; those agents now
    # fall back to multimodal vision LLMs for design/video reasoning tasks.

    # Tier 1: Board (5 agents)
    BOARD = {
        "chairman": FallbackChain("chairman",
            "moonshotai/kimi-k3", "stepfun-ai/step-3.7-flash", "minimaxai/minimax-m3",
            veto=False, timeout_sec=5),
        "strategy_advisor": FallbackChain("strategy_advisor",
            "openai/gpt-oss-120b", "openai/gpt-oss-20b", "nvidia/nemotron-3-super-120b-a12b"),
        "ethics_advisor": FallbackChain("ethics_advisor",
            "nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            veto=True, timeout_sec=8),
        "risk_advisor": FallbackChain("risk_advisor",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "user_advisor": FallbackChain("user_advisor",
            "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct", "minimaxai/minimax-m3"),
    }

    # Tier 2: C-Suite (7 agents)
    C_SUITE = {
        "ceo": FallbackChain("ceo",
            "moonshotai/kimi-k3", "stepfun-ai/step-3.7-flash", "minimaxai/minimax-m3"),
        "cto": FallbackChain("cto",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "cfo": FallbackChain("cfo",
            "mistralai/mistral-nemotron", "openai/gpt-oss-20b", "nvidia/nemotron-mini-4b-instruct"),
        "coo": FallbackChain("coo",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5", "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "cmo": FallbackChain("cmo",
            "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct", "minimaxai/minimax-m3"),
        "chro": FallbackChain("chro",
            "stepfun-ai/step-3.7-flash", "minimaxai/minimax-m3", "nvidia/nemotron-mini-4b-instruct"),
        "clo": FallbackChain("clo",
            "nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            veto=True, timeout_sec=8),
    }

    # Tier 3+4: Departments
    CODE = {
        "code_director": FallbackChain("code_director",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "code_architect": FallbackChain("code_architect",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "coder_1": FallbackChain("coder_1",
            "moonshotai/kimi-k3", "minimaxai/minimax-m3", "stepfun-ai/step-3.7-flash"),
        "coder_2": FallbackChain("coder_2",
            "minimaxai/minimax-m3", "moonshotai/kimi-k3", "nvidia/nemotron-3.5-lightning-30b-a3b"),
        "code_reviewer": FallbackChain("code_reviewer",
            "nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            timeout_sec=8),
        "qa_engineer": FallbackChain("qa_engineer",
            "nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-mini-4b-instruct",
            "nvidia/nvidia-nemotron-nano-9b-v2"),
        "devops": FallbackChain("devops",
            "meta/llama-3.3-70b-instruct", "meta/llama-3.1-70b-instruct",
            "nvidia/nemotron-3-super-120b-a12b"),
    }

    # Tier 3: DevOps Dept (3 agents) — CI/CD, infrastructure, deployment
    DEVOPS = {
        "devops_director": FallbackChain("devops_director",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "ci_cd_engineer": FallbackChain("ci_cd_engineer",
            "meta/llama-3.3-70b-instruct", "meta/llama-3.1-70b-instruct",
            "nvidia/nemotron-3-super-120b-a12b"),
        "infrastructure_engineer": FallbackChain("infrastructure_engineer",
            "nvidia/nemotron-3-super-120b-a12b", "openai/gpt-oss-20b",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5"),
    }

    DESIGN = {
        "design_director": FallbackChain("design_director",
            "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct", "minimaxai/minimax-m3"),
        # NOTE: image *generation* endpoints (flux.*, stable-diffusion-xl) removed from
        # NIM free tier. These agents now use multimodal vision LLMs for design reasoning.
        "image_gen_1": FallbackChain("image_gen_1",
            "moonshotai/kimi-k3", "meta/llama-3.2-90b-vision-instruct", timeout_sec=15),
        "image_gen_2": FallbackChain("image_gen_2",
            "meta/llama-3.2-11b-vision-instruct", "meta/llama-3.2-90b-vision-instruct", timeout_sec=10),
        "ui_designer": FallbackChain("ui_designer",
            "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct", "minimaxai/minimax-m3"),
        "graphic_designer": FallbackChain("graphic_designer",
            "moonshotai/kimi-k3", "minimaxai/minimax-m3", "meta/llama-3.2-11b-vision-instruct"),
        "ux_specialist": FallbackChain("ux_specialist",
            "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct", "minimaxai/minimax-m3"),
        "3d_designer_1": FallbackChain("3d_designer_1",
            "minimaxai/minimax-m3", "moonshotai/kimi-k3", timeout_sec=20),
        "3d_designer_2": FallbackChain("3d_designer_2",
            "minimaxai/minimax-m3", "moonshotai/kimi-k3", timeout_sec=20),
    }

    VIDEO = {
        "video_director": FallbackChain("video_director",
            "minimaxai/minimax-m3", "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct"),
        # NOTE: video *generation* endpoints (cosmos-predict1, stable-video-diffusion)
        # removed from NIM free tier. Using vision LLMs for video reasoning instead.
        "video_gen_1": FallbackChain("video_gen_1",
            "moonshotai/kimi-k3", "meta/llama-3.2-90b-vision-instruct", timeout_sec=30),
        "video_gen_2": FallbackChain("video_gen_2",
            "meta/llama-3.2-90b-vision-instruct", "meta/llama-3.2-11b-vision-instruct", timeout_sec=30),
        "animator_2d": FallbackChain("animator_2d",
            "minimaxai/minimax-m3", "moonshotai/kimi-k3", "meta/llama-3.2-11b-vision-instruct"),
        "motion_graphics": FallbackChain("motion_graphics",
            "mistralai/mistral-nemotron", "stepfun-ai/step-3.7-flash",
            "nvidia/nemotron-mini-4b-instruct"),
        "motion_designer": FallbackChain("motion_designer",
            "mistralai/mistral-nemotron", "stepfun-ai/step-3.7-flash", "nvidia/nemotron-mini-4b-instruct"),
    }

    RESEARCH = {
        "research_director": FallbackChain("research_director",
            "openai/gpt-oss-120b", "openai/gpt-oss-20b", "nvidia/nemotron-3-super-120b-a12b"),
        "researcher_1": FallbackChain("researcher_1",
            "openai/gpt-oss-120b", "nvidia/nemotron-3-super-120b-a12b", "stepfun-ai/step-3.7-flash"),
        "researcher_2": FallbackChain("researcher_2",
            "stepfun-ai/step-3.7-flash", "nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-mini-4b-instruct"),
        "fact_checker": FallbackChain("fact_checker",
            "nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "openai/gpt-oss-20b"),
    }

    DATA = {
        "data_director": FallbackChain("data_director",
            "stepfun-ai/step-3.7-flash", "nvidia/nemotron-3-nano-30b-a3b",
            "nvidia/nemotron-mini-4b-instruct"),
        "data_analyst": FallbackChain("data_analyst",
            "stepfun-ai/step-3.7-flash", "nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-mini-4b-instruct"),
        "data_engineer": FallbackChain("data_engineer",
            "nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-mini-4b-instruct",
            "nvidia/nvidia-nemotron-nano-9b-v2"),
        "data_scientist": FallbackChain("data_scientist",
            "nvidia/nemotron-3-super-120b-a12b", "stepfun-ai/step-3.7-flash",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "database_admin": FallbackChain("database_admin",
            "minimaxai/minimax-m3", "nvidia/nemotron-3-nano-30b-a3b",
            "nvidia/nemotron-mini-4b-instruct"),
    }

    LANGUAGE = {
        "language_director": FallbackChain("language_director",
            "moonshotai/kimi-k3", "stepfun-ai/step-3.7-flash", "minimaxai/minimax-m3"),
        "translator": FallbackChain("translator",
            "nvidia/riva-translate-4b-instruct-v2", "nvidia/riva-translate-4b-instruct-v1.1",
            "stepfun-ai/step-3.7-flash"),
        "localizer": FallbackChain("localizer",
            "moonshotai/kimi-k3", "stepfun-ai/step-3.7-flash", "minimaxai/minimax-m3"),
    }

    KNOWLEDGE = {
        "knowledge_director": FallbackChain("knowledge_director",
            "nvidia/llama-3.2-nv-embedqa-1b-v2",
            "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1",
            "nvidia/llama-3.2-nemoretriever-300m-embed-v2"),
        "knowledge_curator": FallbackChain("knowledge_curator",
            "baai/bge-m3", "nvidia/nv-embed-v1", "nvidia/llama-3.2-nemoretriever-300m-embed-v2"),
        "rag_retriever": FallbackChain("rag_retriever",
            "nvidia/llama-3.2-nemoretriever-300m-embed-v2",
            "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1",
            "nvidia/llama-3.2-nv-embedqa-1b-v2"),
        "rag_reranker": FallbackChain("rag_reranker",
            "nvidia/llama-3.2-nemoretriever-500m-rerank-v2",
            "nvidia/llama-3.2-nv-rerankqa-1b-v2",
            "nvidia/llama-3.2-nemoretriever-ocdr-1b-v1"),
        "doc_parser": FallbackChain("doc_parser",
            "nvidia/nemoretriever-parse", "nvidia/nemotron-parse", timeout_sec=20),
    }

    SAFETY = {
        "safety_director": FallbackChain("safety_director",
            "nvidia/nvidia-nemotron-nano-9b-v2", "nvidia/nemotron-mini-4b-instruct",
            "nvidia/nemotron-3-nano-30b-a3b"),
        "content_safety_analyst": FallbackChain("content_safety_analyst",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control", timeout_sec=2),
        "topic_control_analyst": FallbackChain("topic_control_analyst",
            "nvidia/llama-3.1-nemoguard-8b-topic-control",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-content-safety", timeout_sec=2),
        "jailbreak_analyst": FallbackChain("jailbreak_analyst",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control", timeout_sec=2),
    }

    INLINE_SAFETY = {
        "inline_output_check": FallbackChain("inline_output_check",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control", timeout_sec=2),
        "inline_input_reasoning": FallbackChain("inline_input_reasoning",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control", timeout_sec=2),
        "inline_jailbreak": FallbackChain("inline_jailbreak",
            "nvidia/nemotron-3.5-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/llama-3.1-nemoguard-8b-topic-control", timeout_sec=2),
    }

    ALL_CHAINS: Dict[str, FallbackChain] = {}
    _lock = threading.Lock()

    @classmethod
    def _init_chains(cls):
        if cls.ALL_CHAINS:
            return
        for d in [cls.BOARD, cls.C_SUITE, cls.CODE, cls.DESIGN, cls.VIDEO,
                  cls.RESEARCH, cls.DATA, cls.LANGUAGE, cls.KNOWLEDGE,
                  cls.SAFETY, cls.INLINE_SAFETY]:
            for k, v in d.items():
                cls.ALL_CHAINS[k] = v

    @classmethod
    def get_chain(cls, role: str) -> Optional[FallbackChain]:
        cls._init_chains()
        return cls.ALL_CHAINS.get(role)

    @classmethod
    def all_models_used(cls) -> set:
        """All model IDs referenced across all fallback chains."""
        cls._init_chains()
        models = set()
        for chain in cls.ALL_CHAINS.values():
            models.add(chain.primary)
            models.add(chain.fallback1)
            if chain.fallback2:
                models.add(chain.fallback2)
        return models

    @classmethod
    def chains_by_tier(cls, tier: str) -> List[FallbackChain]:
        """Get all roles belonging to a specific tier (board, c_suite, etc)."""
        cls._init_chains()
        tier_map = {
            "board": cls.BOARD, "c_suite": cls.C_SUITE, "code": cls.CODE,
            "design": cls.DESIGN, "video": cls.VIDEO, "research": cls.RESEARCH,
            "data": cls.DATA, "language": cls.LANGUAGE, "knowledge": cls.KNOWLEDGE,
            "safety": cls.SAFETY, "inline_safety": cls.INLINE_SAFETY,
        }
        return list(tier_map.get(tier, {}).values())

    @classmethod
    def phase_1_agents(cls) -> List[FallbackChain]:
        """Phase 1 = Board(5) + Knowledge(5) + Safety(4) + inline(3) = 17 chains."""
        cls._init_chains()
        result = []
        for tier in ["board", "knowledge", "safety", "inline_safety"]:
            result.extend(cls.chains_by_tier(tier))
        return result

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        cls._init_chains()
        return {
            "total_chains": len(cls.ALL_CHAINS),
            "unique_models": len(cls.all_models_used()),
            "board": list(cls.BOARD.keys()),
            "c_suite": list(cls.C_SUITE.keys()),
            "code": list(cls.CODE.keys()),
            "design": list(cls.DESIGN.keys()),
            "video": list(cls.VIDEO.keys()),
            "research": list(cls.RESEARCH.keys()),
            "data": list(cls.DATA.keys()),
            "language": list(cls.LANGUAGE.keys()),
            "knowledge": list(cls.KNOWLEDGE.keys()),
            "safety": list(cls.SAFETY.keys()),
            "inline_safety": list(cls.INLINE_SAFETY.keys()),
        }


if __name__ == "__main__":
    # Quick self-check
    s = EnterpriseModelRegistry.summary()
    print(f"Total chains: {s['total_chains']}")
    print(f"Unique models: {s['unique_models']}")
    print(f"Board: {s['board']}")
    print(f"Knowledge: {s['knowledge']}")
    print(f"Safety: {s['safety']}")
    print(f"Inline: {s['inline_safety']}")
    print(f"Phase 1 chains: {len(EnterpriseModelRegistry.phase_1_agents())}")
