"""
قسم اللغة (Language Dept) — 3 وكلاء

الوكلاء:
- language_director: مدير القسم (z-ai/glm5.1)
- translator: ترجمة (nvidia/riva-translate-4b-instruct-v2)
- localizer: توطين ثقافي (z-ai/glm5.1)

يدعم: ترجمة بين لغات متعددة، توطين للمحتوى.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


# اللغات المدعومة (ISO 639-1)
SUPPORTED_LANGUAGES = {
    "ar": "Arabic", "en": "English", "fr": "French", "de": "German",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "hi": "Hindi",
    "tr": "Turkish", "nl": "Dutch", "pl": "Polish", "sv": "Swedish",
}


@dataclass
class TranslationResult:
    """نتيجة ترجمة."""
    source_text: str
    source_lang: str
    target_lang: str
    translated_text: str
    confidence: float
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalizationResult:
    """نتيجة توطين ثقافي."""
    original_content: str
    target_locale: str
    localized_content: str
    cultural_notes: List[str] = field(default_factory=list)
    model_used: str = ""


class LanguageAgentBase:
    """الفئة الأساسية لوكلاء اللغة."""

    def __init__(
        self,
        role: str,
        chain,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.role = role
        self.chain = chain
        self.executor = executor
        self.safety = safety
        self.cache = cache or get_default_cache()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _execute(self, prompt: str) -> Dict[str, Any]:
        """ينفذ prompt مع فحص سلامة."""
        try:
            self.safety.check_input(prompt, agent_role=self.role)
        except SafetyViolation as e:
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        result = self.executor.execute(self.role, prompt, chain=self.chain)

        try:
            if result.success and result.output:
                self.safety.check_output(result.output, agent_role=self.role)
        except SafetyViolation as e:
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        return {
            "role": self.role,
            "model": result.chosen_model,
            "output": result.output,
            "success": result.success,
            "latency_ms": result.total_latency_ms,
        }


class LanguageDirector(LanguageAgentBase):
    """مدير قسم اللغة."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("language_director")
        super().__init__("language_director", chain, executor, safety, cache)

    def plan_localization(self, content_type: str, target_locales: List[str]) -> Dict[str, Any]:
        """يخطط لمشروع توطين."""
        prompt = (
            f"As Language Director, plan localization:\n"
            f"Content type: {content_type}\n"
            f"Target locales: {target_locales}\n"
            f"Include: workflow, quality checks, cultural considerations"
        )
        return self._execute(prompt)


class Translator(LanguageAgentBase):
    """مترجم — يستخدم NVIDIA Riva."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("translator")
        super().__init__("translator", chain, executor, safety, cache)

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ar",
    ) -> TranslationResult:
        """يترجم نصاً من لغة إلى أخرى."""
        if source_lang not in SUPPORTED_LANGUAGES:
            return TranslationResult(
                source_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                translated_text=f"ERROR: unsupported source language: {source_lang}",
                confidence=0.0,
                model_used="none",
            )
        if target_lang not in SUPPORTED_LANGUAGES:
            return TranslationResult(
                source_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                translated_text=f"ERROR: unsupported target language: {target_lang}",
                confidence=0.0,
                model_used="none",
            )

        cache_key = f"translate:{self._hash(text)}:{source_lang}:{target_lang}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        prompt = (
            f"Translate from {SUPPORTED_LANGUAGES[source_lang]} to {SUPPORTED_LANGUAGES[target_lang]}:\n"
            f"Text: {text}\n"
            f"Maintain: tone, technical terms, formatting"
        )
        result = self._execute(prompt)

        translation = TranslationResult(
            source_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            translated_text=str(result.get("output", "")),
            confidence=0.85,  # تقدير افتراضي
            model_used=result.get("model", ""),
            metadata={"latency_ms": result.get("latency_ms")},
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, translation, ttl_sec=7200)
        return translation


class Localizer(LanguageAgentBase):
    """موطّن ثقافي — يتكيف مع الثقافة المحلية."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("localizer")
        super().__init__("localizer", chain, executor, safety, cache)

    def localize(self, content: str, target_locale: str) -> LocalizationResult:
        """يوطّن المحتوى ثقافياً."""
        cache_key = f"localize:{self._hash(content)}:{target_locale}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        prompt = (
            f"As Cultural Localizer, adapt this content for {target_locale}:\n"
            f"Content: {content}\n"
            f"Consider: idioms, cultural references, formality, date formats, "
            f"currency, imagery, color symbolism"
        )
        result = self._execute(prompt)

        localization = LocalizationResult(
            original_content=content,
            target_locale=target_locale,
            localized_content=str(result.get("output", "")),
            cultural_notes=self._extract_cultural_notes(str(result.get("output", ""))),
            model_used=result.get("model", ""),
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, localization, ttl_sec=7200)
        return localization

    def _extract_cultural_notes(self, output: str) -> List[str]:
        """يستخرج الملاحظات الثقافية."""
        notes = []
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                notes.append(line.lstrip("-*•0123456789. "))
        return notes[:5]


class LanguageOrchestrator:
    """منسق قسم اللغة."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.director = LanguageDirector(executor, safety, cache)
        self.translator = Translator(executor, safety, cache)
        self.localizer = Localizer(executor, safety, cache)
        self._agents = {
            "language_director": self.director,
            "translator": self.translator,
            "localizer": self.localizer,
        }

    def translate_and_localize(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ar",
        target_locale: str = "ar-SA",
    ) -> Dict[str, Any]:
        """ترجمة + توطين ثقافي."""
        result = {
            "text": text,
            "source": source_lang,
            "target": target_lang,
            "stages": {},
        }

        # 1. ترجمة
        trans = self.translator.translate(text, source_lang, target_lang)
        result["stages"]["translation"] = {
            "translated_text": trans.translated_text[:200],
            "confidence": trans.confidence,
            "model": trans.model_used,
        }

        # 2. توطين ثقافي (يأخذ المخرج من الترجمة)
        localized = self.localizer.localize(
            content=trans.translated_text,
            target_locale=target_locale,
        )
        result["stages"]["localization"] = {
            "locale": localized.target_locale,
            "cultural_notes": len(localized.cultural_notes),
            "model": localized.model_used,
        }

        return result

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل محدد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}
        if role == "translator":
            return agent.translate(
                text=kwargs.get("text", ""),
                source_lang=kwargs.get("source_lang", "en"),
                target_lang=kwargs.get("target_lang", "ar"),
            )
        elif role == "localizer":
            return agent.localize(
                content=kwargs.get("content", ""),
                target_locale=kwargs.get("target_locale", "ar-SA"),
            )
        elif role == "language_director":
            return agent.plan_localization(
                content_type=kwargs.get("content_type", ""),
                target_locales=kwargs.get("target_locales", []),
            )
        return agent._execute(kwargs.get("prompt", ""))


def create_language_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> LanguageOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return LanguageOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    dept = create_language_dept()

    print("=== ترجمة + توطين ===")
    result = dept.translate_and_localize(
        text="Welcome to our platform!",
        source_lang="en",
        target_lang="ar",
        target_locale="ar-SA",
    )
    print(f"المصدر: {result['source']} → الهدف: {result['target']}")
    print(f"الترجمة: {result['stages']['translation']['translated_text'][:100]}")
    print(f"التوطين ({result['stages']['localization']['locale']}): نجح")
    print(f"ملاحظات ثقافية: {result['stages']['localization']['cultural_notes']}")