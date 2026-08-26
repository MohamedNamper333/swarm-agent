"""
Smart Placeholder — ردود محاكية واقعية للاختبار بدون API key.

يصنف النماذج حسب النوع ويولّد ردوداً مفيدة بدل dict فارغ:
- reasoning: توصيات وتحليل
- code: كود وظيفي
- image: وصف تفصيلي
- video: storyboard
- text: ردود نصية عامة
- safety: verdict

هذا يحل المشكلة: بدون NVIDIA_API_KEY، كل الـ agents كانت ترجع
{placeholder: True} فقط ولا يمكن parse output.
"""
import logging
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """أنواع النماذج الرئيسية."""
    REASONING = "reasoning"      # LLM كبيرة للاستدلال
    CODE = "code"                # نماذج code المتخصصة
    IMAGE = "image"              # توليد صور
    VIDEO = "video"              # توليد فيديو
    EMBEDDING = "embedding"       # تمثيل متجهات
    SAFETY = "safety"             # فحص محتوى
    TRANSLATION = "translation"   # ترجمة
    TEXT = "text"                # نص عام (fallback)


# تصنيف النماذج حسب الـ vendor والاسم
# IMPORTANT: more specific patterns must come BEFORE generic ones
MODEL_TYPE_PATTERNS = [
    # Video generation (MUST come before image - "stable-video-diffusion" contains "stabilityai")
    (r"cosmos|sparse|stream|bevformer|changenet", ModelType.VIDEO),
    (r"stable-video-diffusion|runway|sora", ModelType.VIDEO),

    # Image generation
    (r"flux|stabilityai|sdxl", ModelType.IMAGE),
    (r"dall-e|midjourney|imagen", ModelType.IMAGE),

    # Translation
    (r"riva-translate|nllb", ModelType.TRANSLATION),

    # Safety (more specific first)
    (r"nemoguard|jailbreak-detect", ModelType.SAFETY),
    (r"content-safety|topic-control", ModelType.SAFETY),
    (r"gliner-pii|llama-guard|llama-3\.1-nemotron-safety", ModelType.SAFETY),

    # Embeddings (more specific first)
    (r"embedqa|retriever|rerank|embed-code", ModelType.EMBEDDING),
    (r"bge-m3|nvclip|arctic-embed", ModelType.EMBEDDING),

    # Code
    (r"qwen.*coder|codegemma|usdcode", ModelType.CODE),

    # Reasoning (large LLMs) - most common, check last
    (r"nemotron-(3|ultra|super)|llama-(3\.[1-9]|3\.3)", ModelType.REASONING),
    (r"deepseek-v4|kimi-k2|qwen3-next", ModelType.REASONING),
    (r"mistral-(small|medium|large)", ModelType.REASONING),
    (r"gpt-oss|llama-3\.3-70b|llama-3\.2-11b", ModelType.REASONING),

    # Text (small models - default)
    (r"nano|mini|small|gemma-3n|phi-4", ModelType.TEXT),
    (r"nemotron-mini|nemotron-nano|ministral", ModelType.TEXT),
]


def classify_model(model_id: str) -> ModelType:
    """يصنف النموذج حسب اسمه."""
    model_lower = model_id.lower()
    for pattern, mtype in MODEL_TYPE_PATTERNS:
        if re.search(pattern, model_lower):
            return mtype
    return ModelType.TEXT


@dataclass
class PlaceholderResponse:
    """رد placeholder منظم."""
    model: str
    model_type: ModelType
    response_text: str
    structured: Dict[str, Any]
    placeholder: bool = True
    latency_ms: float = 0.0


class SmartPlaceholder:
    """يولّد ردوداً محاكية واقعية حسب نوع النموذج."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate(
        self,
        model_id: str,
        prompt: Any,
        timeout: float = 0.0,
        **kwargs: Any,
    ) -> PlaceholderResponse:
        """يولّد رد placeholder ذكي."""
        model_type = classify_model(model_id)
        prompt_str = str(prompt)
        response_text = self._generate_by_type(model_type, prompt_str, model_id)
        structured = self._build_structured(model_type, prompt_str, response_text)

        # محاكاة latency واقعية
        latency = self._estimate_latency(model_type)

        return PlaceholderResponse(
            model=model_id,
            model_type=model_type,
            response_text=response_text,
            structured=structured,
            latency_ms=latency,
        )

    def _generate_by_type(
        self,
        model_type: ModelType,
        prompt: str,
        model_id: str,
    ) -> str:
        """يولّد رداً نصياً حسب نوع النموذج."""
        generators = {
            ModelType.REASONING: self._gen_reasoning,
            ModelType.CODE: self._gen_code,
            ModelType.IMAGE: self._gen_image,
            ModelType.VIDEO: self._gen_video,
            ModelType.EMBEDDING: self._gen_embedding,
            ModelType.SAFETY: self._gen_safety,
            ModelType.TRANSLATION: self._gen_translation,
            ModelType.TEXT: self._gen_text,
        }
        generator = generators.get(model_type, self._gen_text)
        return generator(prompt, model_id)

    def _gen_reasoning(self, prompt: str, model_id: str) -> str:
        """رد للاستدلال."""
        prompt_summary = prompt[:150].replace("\n", " ")
        templates = [
            f"Based on careful analysis of '{prompt_summary}...', I recommend a measured approach. "
            "Key considerations: risk mitigation, stakeholder alignment, and phased rollout. "
            "Decision: APPROVE with conditions. "
            "Reasoning: The proposed action aligns with strategic objectives while maintaining safety margins.",

            f"Analyzing '{prompt_summary}...'. "
            "My assessment: this requires multi-stakeholder review. "
            "Recommendation: ESCALATE to board for final decision. "
            "Rationale: Impact spans multiple departments and requires coordinated response.",

            f"Reviewing '{prompt_summary}...'. "
            "Conclusion: REJECT due to potential risks. "
            "Alternative: A modified approach with stricter guardrails would be more appropriate.",
        ]
        return random.choice(templates)

    def _gen_code(self, prompt: str, model_id: str) -> str:
        """رد للكود."""
        prompt_summary = prompt[:80].replace("\n", " ")
        templates = [
            f"""```python
# Solution for: {prompt_summary}...

from typing import Optional


def solution(input_data: str) -> dict:
    \"\"\"Process the input and return results.\"\"\"
    if not input_data:
        return {{"status": "error", "message": "empty input"}}

    # Implementation
    result = {{
        "status": "success",
        "data": input_data.strip().lower(),
        "timestamp": "2026-08-12",
    }}
    return result


if __name__ == "__main__":
    print(solution("test"))
```""",

            f"""```python
# Alternative implementation for: {prompt_summary}...

class Handler:
    def __init__(self):
        self.state = {{"count": 0, "errors": []}}

    def process(self, request):
        try:
            self.state["count"] += 1
            return {{"ok": True, "result": request}}
        except Exception as e:
            self.state["errors"].append(str(e))
            return {{"ok": False, "error": str(e)}}
```""",
        ]
        return random.choice(templates)

    def _gen_image(self, prompt: str, model_id: str) -> str:
        """رد لتوليد الصور."""
        prompt_summary = prompt[:100].replace("\n", " ")
        templates = [
            f"Generated image: A detailed depiction of '{prompt_summary}...'. "
            "Resolution: 1024x1024, Format: PNG. "
            "Style: photorealistic, lighting: natural, composition: centered.",

            f"Image asset created for prompt: '{prompt_summary}...'. "
            "Output: base64-encoded PNG, 2048x2048. "
            "Color palette: vibrant, mood: professional.",
        ]
        return random.choice(templates)

    def _gen_video(self, prompt: str, model_id: str) -> str:
        """رد لتوليد الفيديو."""
        prompt_summary = prompt[:100].replace("\n", " ")
        templates = [
            f"Video storyboard for '{prompt_summary}...': "
            "Frame 1: opening shot (3s), Frame 2: main content (15s), Frame 3: closing (5s). "
            "Duration: 23s, FPS: 30, Resolution: 1080p.",

            f"Generated video: '{prompt_summary}...'. "
            "Format: MP4, Duration: 10s, Codec: H.264, Resolution: 720p.",
        ]
        return random.choice(templates)

    def _gen_embedding(self, prompt: str, model_id: str) -> str:
        """رد للـ embeddings."""
        # Embeddings always return a vector (as string for compat)
        import hashlib
        h = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        # محاكاة 768-dim embedding
        values = [int(c, 16) / 15.0 for c in h] * 48  # 16 * 48 = 768
        values = values[:768]
        return f"[{','.join(f'{v:.4f}' for v in values[:20])}...]"  # truncated

    def _gen_safety(self, prompt: str, model_id: str) -> str:
        """رد لفحص المحتوى."""
        prompt_lower = prompt.lower()
        # كشف أولي بسيط
        if any(w in prompt_lower for w in ["ssn", "credit card", "password", "kill"]):
            verdict = "unsafe"
            confidence = 95
        elif any(w in prompt_lower for w in ["ignore all previous", "jailbreak", "bypass"]):
            verdict = "unsafe"
            confidence = 98
        elif any(w in prompt_lower for w in ["harm", "violence", "illegal"]):
            verdict = "unsafe"
            confidence = 85
        else:
            verdict = "safe"
            confidence = 75
        return f"Verdict: {verdict}, confidence: {confidence}, model: {model_id}"

    def _gen_translation(self, prompt: str, model_id: str) -> str:
        """رد للترجمة."""
        # محاولة كشف اللغة
        if any(ord(c) > 1536 for c in prompt):
            # قد يكون عربي
            return f"[TRANSLATED from Arabic]: {prompt[:100]}"
        return f"[TRANSLATED to target]: {prompt[:100]}"

    def _gen_text(self, prompt: str, model_id: str) -> str:
        """رد نصي عام."""
        prompt_summary = prompt[:100].replace("\n", " ")
        templates = [
            f"Response to '{prompt_summary}...': I understand the request. "
            "Here's a summary: the task requires careful planning and execution.",

            f"Analyzing '{prompt_summary}...'. "
            "My recommendation: proceed with the standard approach. "
            "Key points: maintain quality, follow best practices, iterate as needed.",
        ]
        return random.choice(templates)

    def _build_structured(
        self,
        model_type: ModelType,
        prompt: str,
        response_text: str,
    ) -> Dict[str, Any]:
        """يبني dict منظم للـ output."""
        base = {
            "model_type": model_type.value,
            "prompt_preview": prompt[:100],
            "response": response_text,
            "placeholder": True,
        }

        if model_type == ModelType.EMBEDDING:
            # إضافة embedding وهمي
            base["embedding_dim"] = 768
            base["embedding_preview"] = response_text[:80]
        elif model_type == ModelType.SAFETY:
            # parse verdict
            if "verdict: safe" in response_text.lower():
                base["verdict"] = "safe"
            elif "verdict: unsafe" in response_text.lower():
                base["verdict"] = "unsafe"
            else:
                base["verdict"] = "unknown"
            # extract confidence
            match = re.search(r"confidence:\s*(\d+)", response_text)
            if match:
                base["confidence"] = int(match.group(1))
        elif model_type == ModelType.CODE:
            # إضافة indicator
            base["language"] = "python"
            base["has_code"] = "```" in response_text

        return base

    def _estimate_latency(self, model_type: ModelType) -> float:
        """يقدّر latency واقعية (ms)."""
        base_latency = {
            ModelType.REASONING: 800,
            ModelType.CODE: 600,
            ModelType.IMAGE: 2000,
            ModelType.VIDEO: 5000,
            ModelType.EMBEDDING: 100,
            ModelType.SAFETY: 200,
            ModelType.TRANSLATION: 300,
            ModelType.TEXT: 400,
        }
        base = base_latency.get(model_type, 500)
        # إضافة variance
        return base + random.uniform(0, base * 0.3)


# Singleton
_default_placeholder: Optional[SmartPlaceholder] = None


def get_default_placeholder() -> SmartPlaceholder:
    """يرجع الـ placeholder الافتراضي."""
    global _default_placeholder
    if _default_placeholder is None:
        _default_placeholder = SmartPlaceholder()
    return _default_placeholder


# دالة تكامل مع FallbackChainExecutor
def smart_placeholder_call(
    model_id: str,
    prompt: Any,
    timeout: float = 0.0,
    **kwargs: Any,
) -> Dict[str, Any]:
    """دالة placeholder تستخدم SmartPlaceholder.

    متوافقة مع interface الـ FallbackChainExecutor.
    """
    placeholder = get_default_placeholder()
    response = placeholder.generate(model_id, prompt, timeout=timeout, **kwargs)
    # Return as dict for backward compatibility
    return {
        "model": response.model,
        "model_type": response.model_type.value,
        "response": response.response_text,
        "structured": response.structured,
        "placeholder": True,
        "latency_ms": response.latency_ms,
    }


if __name__ == "__main__":
    # اختبار سريع
    placeholder = SmartPlaceholder(seed=42)

    test_models = [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "qwen/qwen2.5-coder-32b-instruct",
        "black-forest-labs/flux.1-dev",
        "nvidia/cosmos-predict1-7b",
        "nvidia/llama-3.2-nv-embedqa-1b-v2",
        "nvidia/llama-3.1-nemoguard-8b-content-safety",
        "nvidia/riva-translate-4b-instruct-v2",
        "nvidia/nemotron-mini-4b-instruct",
    ]

    print("=== SmartPlaceholder Tests ===")
    for model in test_models:
        resp = placeholder.generate(model, "test prompt")
        print(f"\n{model}")
        print(f"  type: {resp.model_type.value}")
        print(f"  response: {resp.response_text[:80]}...")
        print(f"  latency: {resp.latency_ms:.0f}ms")