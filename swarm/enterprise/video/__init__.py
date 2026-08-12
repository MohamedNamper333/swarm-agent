"""
قسم الفيديو (Video Dept) — 6 وكلاء

الوكلاء:
- video_director: مدير القسم، ينسق بين الوكلاء
- video_gen_1: توليد فيديو (cosmos-predict1-7b)
- video_gen_2: توليد فيديو (stable-video-diffusion)
- animator_1: تحريك (minimax-m3)
- animator_2: تحريك (minimax-m3)
- motion_designer: تصميم حركة (mistral-medium-3.5)

يدعم: MP4/WebM للحركة، GIF للحلقات القصيرة.
"""
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


class VideoFormat(str, Enum):
    """صيغ الفيديو."""
    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"
    MOV = "mov"


class VideoDuration(str, Enum):
    """مدد الفيديو."""
    SHORT = "3-5s"   # للحلقات
    MEDIUM = "10-30s"  # للمحتوى
    LONG = "60s+"     # للعروض


@dataclass
class VideoAsset:
    """أصل فيديو مُولّد."""
    format: VideoFormat
    duration: VideoDuration
    content: str  # URL أو base64 أو path
    prompt: str
    author: str
    fps: int = 30
    resolution: str = "1080p"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnimationPlan:
    """خطة تحريك."""
    target: str
    keyframes: List[str]
    transitions: List[str]
    timing_ms: List[int]
    easing: str = "ease-in-out"


class VideoAgentBase:
    """الفئة الأساسية لوكلاء الفيديو."""

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


class VideoDirector(VideoAgentBase):
    """مدير قسم الفيديو."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("video_director")
        super().__init__("video_director", chain, executor, safety, cache)

    def plan_video_project(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """يخطط لمشروع فيديو كامل."""
        prompt = (
            f"As Video Director, plan this video project:\n{brief}\n"
            f"Include: shot list, transitions, music cues, narration timing, "
            f"target duration, deliverables"
        )
        return self._execute(prompt)


class VideoGeneratorBase(VideoAgentBase):
    """فئة أساسية لمولّدات الفيديو."""

    @abstractmethod
    def get_engine_name(self) -> str:
        """اسم محرك التوليد."""
        pass

    def generate(
        self,
        prompt: str,
        duration: VideoDuration = VideoDuration.SHORT,
        format: VideoFormat = VideoFormat.MP4,
        fps: int = 30,
    ) -> VideoAsset:
        """يولّد فيديو."""
        cache_key = f"gen:{self._hash(prompt)}:{duration.value}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        full_prompt = (
            f"Generate video: {prompt}\n"
            f"Engine: {self.get_engine_name()}\n"
            f"Duration: {duration.value}\n"
            f"FPS: {fps}\n"
            f"Format: {format.value}"
        )
        result = self._execute(full_prompt)

        asset = VideoAsset(
            format=format,
            duration=duration,
            content=str(result.get("output", "")),
            prompt=prompt,
            author=self.role,
            fps=fps,
            resolution="1080p",
            metadata={
                "model": result.get("model"),
                "engine": self.get_engine_name(),
                "latency_ms": result.get("latency_ms"),
            },
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, asset, ttl_sec=3600)
        return asset


class VideoGen1(VideoGeneratorBase):
    """مولّد فيديو #1 — nvidia/cosmos-predict1-7b (image-to-video)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("video_gen_1")
        super().__init__("video_gen_1", chain, executor, safety, cache)

    def get_engine_name(self) -> str:
        return "cosmos-predict1-7b"


class VideoGen2(VideoGeneratorBase):
    """مولّد فيديو #2 — stabilityai/stable-video-diffusion."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("video_gen_2")
        super().__init__("video_gen_2", chain, executor, safety, cache)

    def get_engine_name(self) -> str:
        return "stable-video-diffusion"


class AnimatorBase(VideoAgentBase):
    """فئة أساسية للمحرّكين (animators)."""

    @abstractmethod
    def get_style(self) -> str:
        """الأسلوب (2D/3D/stop-motion)."""
        pass

    def animate(
        self,
        scene: str,
        keyframes: Optional[List[str]] = None,
    ) -> AnimationPlan:
        """يخطّط لتحريك مشهد."""
        prompt = (
            f"As {self.get_style()} animator, plan animation:\n"
            f"Scene: {scene}\n"
            f"Keyframes: {keyframes or 'auto'}\n"
            f"Provide: keyframes, transitions, timing, easing"
        )
        result = self._execute(prompt)
        return AnimationPlan(
            target=scene,
            keyframes=keyframes or [],
            transitions=["fade", "slide"],
            timing_ms=[0, 500, 1000],
            easing="ease-in-out",
        )


class Animator1(AnimatorBase):
    """محرّك #1 — minimaxai/minimax-m3 (متعدد الأساليب)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("animator_1")
        super().__init__("animator_1", chain, executor, safety, cache)

    def get_style(self) -> str:
        return "mixed"


class Animator2(AnimatorBase):
    """محرّك #2 — minimaxai/minimax-m3 (fallback)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("animator_2")
        super().__init__("animator_2", chain, executor, safety, cache)

    def get_style(self) -> str:
        return "cinematic"


class MotionDesigner(VideoAgentBase):
    """مصمم حركة — timing، easing، transitions."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("motion_designer")
        super().__init__("motion_designer", chain, executor, safety, cache)

    def design_motion_grammar(self, content: str) -> Dict[str, Any]:
        """يصمم قواعد الحركة للمحتوى."""
        prompt = (
            f"As Motion Designer, create motion grammar for:\n{content}\n"
            f"Include: easing curves, timing functions, motion paths, "
            f"transitions, micro-interactions"
        )
        return self._execute(prompt)


class VideoOrchestrator:
    """منسق قسم الفيديو."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.director = VideoDirector(executor, safety, cache)
        self.gen_1 = VideoGen1(executor, safety, cache)
        self.gen_2 = VideoGen2(executor, safety, cache)
        self.animator_1 = Animator1(executor, safety, cache)
        self.animator_2 = Animator2(executor, safety, cache)
        self.motion = MotionDesigner(executor, safety, cache)
        self._agents = {
            "video_director": self.director,
            "video_gen_1": self.gen_1,
            "video_gen_2": self.gen_2,
            "animator_1": self.animator_1,
            "animator_2": self.animator_2,
            "motion_designer": self.motion,
        }

    def create_promo_video(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """ينشئ فيديو ترويجي كامل."""
        result = {
            "brief": brief,
            "stages": {},
        }

        # 1. خطة المشروع
        plan = self.director.plan_video_project(brief)
        result["stages"]["plan"] = {
            "model": plan.get("model"),
            "latency_ms": plan.get("latency_ms"),
        }

        # 2. توليد الفيديو (يستخدم gen_1)
        video = self.gen_1.generate(
            prompt=brief.get("description", ""),
            duration=VideoDuration.MEDIUM,
            format=VideoFormat.MP4,
        )
        result["stages"]["video_generated"] = {
            "format": video.format.value,
            "duration": video.duration.value,
            "author": video.author,
            "fps": video.fps,
            "engine": video.metadata.get("engine"),
        }

        # 3. تخطيط التحريك
        animation = self.animator_1.animate(
            scene=brief.get("description", ""),
            keyframes=["intro", "main", "outro"],
        )
        result["stages"]["animation"] = {
            "keyframes": animation.keyframes,
            "transitions": animation.transitions,
            "easing": animation.easing,
        }

        # 4. تصميم الحركة
        motion = self.motion.design_motion_grammar(
            content=brief.get("description", "")
        )
        result["stages"]["motion_design"] = {
            "model": motion.get("model"),
            "has_grammar": "output" in motion and bool(motion.get("output")),
        }

        return result

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل محدد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}

        if role in ("video_gen_1", "video_gen_2"):
            duration = VideoDuration(kwargs.get("duration", "3-5s"))
            fmt = VideoFormat(kwargs.get("format", "mp4"))
            return agent.generate(
                prompt=kwargs.get("prompt", ""),
                duration=duration,
                format=fmt,
            )
        elif role in ("animator_1", "animator_2"):
            return agent.animate(kwargs.get("scene", ""))
        elif role == "video_director":
            return agent.plan_video_project(kwargs.get("brief", {}))
        elif role == "motion_designer":
            return agent.design_motion_grammar(kwargs.get("content", ""))
        else:
            return agent._execute(kwargs.get("prompt", ""))


def create_video_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> VideoOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return VideoOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    dept = create_video_dept()

    print("=== Promo Video ===")
    brief = {
        "title": "Product Launch",
        "description": "30-second promo for AI assistant launch",
        "target_audience": "developers",
    }
    result = dept.create_promo_video(brief)
    print(f"العنوان: {result['brief']['title']}")
    print(f"المراحل: {len(result['stages'])}")
    for stage, info in result['stages'].items():
        print(f"  - {stage}: {info}")