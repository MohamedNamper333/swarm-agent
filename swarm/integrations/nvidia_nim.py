"""NVIDIA NIM API client (OpenAI-compatible).

Endpoint: https://integrate.api.nvidia.com/v1
Auth: Bearer $NVIDIA_API_KEY (free tier / trial).

All models are exposed via chat completions with OpenAI-compatible schema.
Visual models use the /gen image endpoint pattern.
Embedding models use /embeddings.
"""

from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

LOG = logging.getLogger(__name__)

NVIDIA_NIM_BASE = "https://integrate.api.nvidia.com/v1"


class NIMError(Exception):
    """Base exception for NVIDIA NIM API errors."""


class NIMAuthError(NIMError):
    """Missing or invalid API key."""


class NIRateLimitError(NIMError):
    """429: daily/trial limit hit."""

    def __init__(self, model: str, retry_after: Optional[float] = None):
        super().__init__(f"Rate limit hit for {model}")
        self.model = model
        self.retry_after = retry_after


class NIMTimeoutError(NIMError):
    """Request timed out."""


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatCompletionResult:
    model: str
    content: str
    finish_reason: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_seconds: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


class NVIDIANIMClient:
    """Thin client for the NVIDIA NIM integrate API.

    - Synchronous requests only (Phase 1 W1).
    - No retries here: callers (fallback_chain) decide policy.
    - Surfaces 429 distinctly so the chain can swap to fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = NVIDIA_NIM_BASE,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key:
            raise NIMAuthError(
                "NVIDIA_API_KEY env var not set. Get a free key at "
                "https://build.nvidia.com (no card required for trial)."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    # ------------------------------------------------------------
    # Chat completions
    # ------------------------------------------------------------
    def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        stream: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ChatCompletionResult:
        """Send a chat completion request.

        `model` is the fully-qualified NIM id like
        "nvidia/nemotron-3-ultra-550b-a55b" or
        "deepseek-ai/deepseek-v4-pro".
        """
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }
        if extra:
            payload.update(extra)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        t0 = time.monotonic()
        try:
            resp = self.session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise NIMTimeoutError(
                f"NIM chat timeout after {self.timeout}s for {model}"
            ) from exc
        except requests.RequestException as exc:
            raise NIMError(f"NIM network error for {model}: {exc}") from exc

        latency = time.monotonic() - t0

        if resp.status_code == 429:
            retry_after = None
            try:
                retry_after = float(resp.headers.get("Retry-After", ""))
            except (TypeError, ValueError):
                pass
            raise NIRateLimitError(model, retry_after)

        if resp.status_code == 401 or resp.status_code == 403:
            raise NIMAuthError(
                f"NIM auth failed ({resp.status_code}) — check API key"
            )

        if not resp.ok:
            body = resp.text[:500]
            raise NIMError(
                f"NIM {model} returned HTTP {resp.status_code}: {body}"
            )

        data = resp.json()
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish = choice.get("finish_reason", "stop")
        except (KeyError, IndexError) as exc:
            raise NIMError(f"NIM {model} returned malformed body: {data}") from exc

        return ChatCompletionResult(
            model=model,
            content=content,
            finish_reason=finish,
            usage=data.get("usage", {}),
            latency_seconds=latency,
            raw=data,
        )

    # ------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------
    def embed(
        self,
        model: str,
        input_text: List[str],
        encoding_format: str = "float",
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": model,
            "input": input_text,
            "encoding_format": encoding_format,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self.session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise NIMTimeoutError(
                f"NIM embed timeout after {self.timeout}s for {model}"
            ) from exc

        if resp.status_code == 429:
            raise NIRateLimitError(model)
        if not resp.ok:
            raise NIMError(f"NIM embed HTTP {resp.status_code}: {resp.text[:300]}")

        return resp.json()

    # ------------------------------------------------------------
    # Image generation (FLUX, Stable Diffusion)
    # ------------------------------------------------------------
    def generate_image(
        self,
        model: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 28,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate an image and return base64 PNG payload under
        `data[0].b64_json` (matches the gen image endpoint shape)."""
        url = f"{self.base_url}/gen"
        # FLUX uses width/height, SD uses width/height too. Pass both.
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": num_inference_steps,
            "cfg_scale": guidance_scale,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = seed

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self.session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise NIMTimeoutError(
                f"NIM image timeout after {self.timeout}s for {model}"
            ) from exc

        if resp.status_code == 429:
            raise NIRateLimitError(model)
        if not resp.ok:
            raise NIMError(
                f"NIM image HTTP {resp.status_code}: {resp.text[:300]}"
            )

        return resp.json()


def make_default_client(api_key: Optional[str] = None) -> NVIDIANIMClient:
    """Factory used by tests and runtime. Reads NVIDIA_API_KEY from env."""
    return NVIDIANIMClient(api_key=api_key)
