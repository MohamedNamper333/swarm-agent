"""
قسم التصميم (Design Dept) — 8 وكلاء

الوكلاء:
- design_director: مدير القسم، ينسق بين المصممين
- image_gen_1: توليد صور عالية الجودة (FLUX.1-dev)
- image_gen_2: توليد صور سريع (FLUX.2-klein-4b)
- designer_1: تصميم UI/UX (thinking machines/inkling)
- designer_2: تصميم UI/UX
- ux_specialist: خبير تجربة المستخدم (kimi-k2.5)
- 3d_designer_1: نمذجة ثلاثية الأبعاد (microsoft/trellis)
- 3d_designer_2: نمذجة ثلاثية الأبعاد

كل وكيل يستخدم chain مخصص من registry مع inline safety filter.
"""
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """أنواع الأصول التصميمية."""
    IMAGE = "image"
    UI_MOCKUP = "ui_mockup"
    LOGO = "logo"
    ICON = "icon"
    ILLUSTRATION = "illustration"
    MODEL_3D = "model_3d"
    TEXTURE = "texture"
    ANIMATION = "animation"


class OutputFormat(str, Enum):
    """صيغ الإخراج."""
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    GLB = "glb"  # 3D
    FBX = "fbx"  # 3D
    OBJ = "obj"  # 3D


@dataclass
class DesignAsset:
    """أصل تصميمي مُولّد."""
    asset_type: AssetType
    format: OutputFormat
    content: Union[bytes, str, Dict]  # binary للملفات، string لـ SVG/text، dict لـ metadata
    prompt: str
    author: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignReview:
    """مراجعة تصميم."""
    asset_id: str
    approved: bool
    score: int  # 0-100
    feedback: str
    suggestions: List[str] = field(default_factory=list)


class DesignAgentBase:
    """الفئة الأساسية لوكلاء التصميم."""

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


class DesignDirector(DesignAgentBase):
    """مدير قسم التصميم — ينسق بين المصممين."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("design_director")
        super().__init__("design_director", chain, executor, safety, cache)

    def assign_design_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """يوزّع مهمة تصميم على الوكيل المناسب."""
        prompt = (
            f"As Design Director, decide which design agent should handle this:\n"
            f"Task: {task}\n"
            f"Available: image_gen_1 (quality), image_gen_2 (speed), "
            f"designer_1/2 (UI), ux_specialist, 3d_designer_1/2\n"
            f"Return: assigned_agent, brief"
        )
        return self._execute(prompt)


class ImageGeneratorBase(DesignAgentBase):
    """فئة أساسية لمولّدات الصور."""

    @abstractmethod
    def get_quality_level(self) -> str:
        """مستوى الجودة (quality/speed)."""
        pass

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        negative_prompt: str = "",
    ) -> DesignAsset:
        """يولّد صورة."""
        cache_key = f"gen:{self._hash(prompt)}:{width}x{height}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        full_prompt = (
            f"Generate image: {prompt}\n"
            f"Size: {width}x{height}\n"
            f"Quality: {self.get_quality_level()}\n"
            f"Negative: {negative_prompt}"
        )
        result = self._execute(full_prompt)

        asset = DesignAsset(
            asset_type=AssetType.IMAGE,
            format=OutputFormat.PNG,
            content=str(result.get("output", "")),  # placeholder - base64 or url
            prompt=prompt,
            author=self.role,
            metadata={
                "model": result.get("model"),
                "latency_ms": result.get("latency_ms"),
                "width": width,
                "height": height,
                "quality": self.get_quality_level(),
            },
        )

        if "error" not in result:
            self.cache.set(self.role, cache_key, asset, ttl_sec=3600)
        return asset


class ImageGen1(ImageGeneratorBase):
    """مولّد صور عالي الجودة — FLUX.1-dev."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("image_gen_1")
        super().__init__("image_gen_1", chain, executor, safety, cache)

    def get_quality_level(self) -> str:
        return "quality"


class ImageGen2(ImageGeneratorBase):
    """مولّد صور سريع — FLUX.2-klein-4b."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("image_gen_2")
        super().__init__("image_gen_2", chain, executor, safety, cache)

    def get_quality_level(self) -> str:
        return "speed"


class DesignerBase(DesignAgentBase):
    """فئة أساسية للمصممين (UI/UX/Graphic)."""

    def design(self, requirements: str, asset_type: AssetType = AssetType.UI_MOCKUP) -> DesignAsset:
        """يصمم أصلاً."""
        prompt = (
            f"As expert designer, create {asset_type.value}:\n"
            f"Requirements: {requirements}\n"
            f"Provide: layout, colors, typography, components, accessibility considerations"
        )
        result = self._execute(prompt)

        return DesignAsset(
            asset_type=asset_type,
            format=OutputFormat.SVG,
            content=str(result.get("output", "")),
            prompt=requirements,
            author=self.role,
            metadata={"model": result.get("model"), "latency_ms": result.get("latency_ms")},
        )


class Designer1(DesignerBase):
    """مصمم 1 — thinking machines/inkling."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("designer_1")
        super().__init__("designer_1", chain, executor, safety, cache)


class Designer2(DesignerBase):
    """مصمم 2 — thinking machines/inkling."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("designer_2")
        super().__init__("designer_2", chain, executor, safety, cache)


class UXSpecialist(DesignAgentBase):
    """خبير تجربة المستخدم — تحليل UX، accessibility، user flows."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("ux_specialist")
        super().__init__("ux_specialist", chain, executor, safety, cache)

    def analyze_ux(self, design_spec: str) -> Dict[str, Any]:
        """يحلل UX لتصميم معين."""
        prompt = (
            f"As UX Specialist, analyze this design:\n{design_spec}\n"
            f"Evaluate: usability, accessibility (WCAG), user flows, "
            f"cognitive load, error handling"
        )
        return self._execute(prompt)

    def generate_user_flow(self, feature: str) -> Dict[str, Any]:
        """يولّد user flow."""
        prompt = (
            f"Generate user flow for: {feature}\n"
            f"Include: entry points, decision points, error states, success states"
        )
        return self._execute(prompt)


class ThreeDDesignerBase(DesignAgentBase):
    """فئة أساسية لمصممي 3D."""

    @abstractmethod
    def get_format(self) -> OutputFormat:
        """الصيغة المفضلة."""
        pass

    def generate_3d(
        self,
        description: str,
        format: Optional[OutputFormat] = None,
    ) -> DesignAsset:
        """يولّد نموذج 3D."""
        fmt = format or self.get_format()
        prompt = (
            f"Generate 3D model: {description}\n"
            f"Format: {fmt.value}\n"
            f"Include: vertices, textures, materials, scale"
        )
        result = self._execute(prompt)

        return DesignAsset(
            asset_type=AssetType.MODEL_3D,
            format=fmt,
            content=str(result.get("output", "")),
            prompt=description,
            author=self.role,
            metadata={"model": result.get("model"), "format": fmt.value},
        )


class ThreeDDesigner1(ThreeDDesignerBase):
    """مصمم 3D #1 — microsoft/trellis."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("3d_designer_1")
        super().__init__("3d_designer_1", chain, executor, safety, cache)

    def get_format(self) -> OutputFormat:
        return OutputFormat.GLB


class ThreeDDesigner2(ThreeDDesignerBase):
    """مصمم 3D #2 — microsoft/trellis (fallback)."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("3d_designer_2")
        super().__init__("3d_designer_2", chain, executor, safety, cache)

    def get_format(self) -> OutputFormat:
        return OutputFormat.FBX


class DesignOrchestrator:
    """منسق قسم التصميم."""

    def __init__(
        self,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.director = DesignDirector(executor, safety, cache)
        self.image_gen_1 = ImageGen1(executor, safety, cache)
        self.image_gen_2 = ImageGen2(executor, safety, cache)
        self.designer_1 = Designer1(executor, safety, cache)
        self.designer_2 = Designer2(executor, safety, cache)
        self.ux = UXSpecialist(executor, safety, cache)
        self.d3d_1 = ThreeDDesigner1(executor, safety, cache)
        self.d3d_2 = ThreeDDesigner2(executor, safety, cache)
        self._agents = {
            "design_director": self.director,
            "image_gen_1": self.image_gen_1,
            "image_gen_2": self.image_gen_2,
            "designer_1": self.designer_1,
            "designer_2": self.designer_2,
            "ux_specialist": self.ux,
            "3d_designer_1": self.d3d_1,
            "3d_designer_2": self.d3d_2,
        }

    def generate_complete_brand_kit(self, brand_name: str) -> Dict[str, Any]:
        """يولّد brand kit كامل: logo + صور + UI mockup + UX analysis."""
        result = {
            "brand": brand_name,
            "assets": {},
            "stages": {},
        }

        # 1. Logo (quality image)
        logo = self.image_gen_1.generate(
            prompt=f"minimalist logo for {brand_name}, clean vector style",
            width=512,
            height=512,
        )
        result["assets"]["logo"] = {
            "type": logo.asset_type.value,
            "format": logo.format.value,
            "author": logo.author,
            "preview": str(logo.content)[:200] if logo.content else "no output",
        }

        # 2. Hero image
        hero = self.image_gen_2.generate(
            prompt=f"hero image for {brand_name} landing page, modern aesthetic",
            width=1920,
            height=1080,
        )
        result["assets"]["hero_image"] = {
            "type": hero.asset_type.value,
            "author": hero.author,
            "preview": str(hero.content)[:200] if hero.content else "no output",
        }

        # 3. UI mockup
        ui = self.designer_1.design(
            requirements=f"landing page mockup for {brand_name}, modern design",
            asset_type=AssetType.UI_MOCKUP,
        )
        result["assets"]["ui_mockup"] = {
            "type": ui.asset_type.value,
            "author": ui.author,
            "preview": str(ui.content)[:200] if ui.content else "no output",
        }

        # 4. UX analysis
        ux_analysis = self.ux.analyze_ux(
            design_spec=f"Brand kit for {brand_name}: logo + hero + landing page"
        )
        result["stages"]["ux_analysis"] = {
            "model": ux_analysis.get("model"),
            "latency_ms": ux_analysis.get("latency_ms"),
            "has_feedback": "output" in ux_analysis and bool(ux_analysis.get("output")),
        }

        return result

    def run_agent(self, role: str, **kwargs) -> Any:
        """يشغّل وكيل محدد."""
        agent = self._agents.get(role)
        if not agent:
            return {"error": f"unknown role: {role}"}

        if role in ("image_gen_1", "image_gen_2"):
            return agent.generate(
                prompt=kwargs.get("prompt", ""),
                width=kwargs.get("width", 1024),
                height=kwargs.get("height", 1024),
            )
        elif role in ("designer_1", "designer_2"):
            return agent.design(
                requirements=kwargs.get("requirements", ""),
                asset_type=AssetType(kwargs.get("asset_type", "ui_mockup")),
            )
        elif role == "ux_specialist":
            return agent.analyze_ux(kwargs.get("design_spec", ""))
        elif role in ("3d_designer_1", "3d_designer_2"):
            return agent.generate_3d(kwargs.get("description", ""))
        elif role == "design_director":
            return agent.assign_design_task(kwargs.get("task", {}))
        else:
            return agent._execute(kwargs.get("prompt", ""))


def create_design_dept(
    executor: Optional[FallbackChainExecutor] = None,
    safety: Optional[InlineSafetyFilter] = None,
    cache=None,
) -> DesignOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return DesignOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    dept = create_design_dept()

    print("=== Brand Kit Generation ===")
    kit = dept.generate_complete_brand_kit("TechStartup")
    print(f"العلامة التجارية: {kit['brand']}")
    print(f"الأصول المُولّدة: {len(kit['assets'])}")
    for name, asset in kit['assets'].items():
        print(f"  - {name}: {asset.get('author')} ({asset.get('type')})")
    print(f"UX analysis: {kit['stages']['ux_analysis']}")