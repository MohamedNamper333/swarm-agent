"""
Task Classifier - Classify tasks by type and assess complexity
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    CREATIVE = "creative"
    SECURITY = "security"
    RESEARCH = "research"
    IMPLEMENTATION = "implementation"
    DEBUG = "debug"
    REFACTOR = "refactor"
    QUICK_FIX = "quick_fix"


@dataclass
class TaskClassification:
    task_type: TaskType
    confidence: float
    complexity: int
    keywords_matched: List[str]
    reasoning: str


class TaskClassifier:
    """Classifies tasks by type and assesses complexity."""

    # Keyword patterns for each task type
    PATTERNS = {
        TaskType.CREATIVE: {
            "keywords": ["brainstorm", "idea", "creative", "innovate", "prototype", "vision", "concept", "ideate"],
            "weight": 1.0
        },
        TaskType.SECURITY: {
            "keywords": ["security", "vulnerability", "threat", "audit", "penetration", "exploit", "hack", "secure", "encryption", "vulnerability"],
            "weight": 1.3
        },
        TaskType.RESEARCH: {
            "keywords": ["research", "find", "explore", "investigate", "compare", "analyze", "study", "survey", "literature", "benchmark", "best practices", "evaluate"],
            "weight": 1.5
        },
        TaskType.DEBUG: {
            "keywords": ["debug", "fix", "error", "bug", "issue", "broken", "crash", "fail", "exception", "traceback"],
            "weight": 1.3
        },
        TaskType.REFACTOR: {
            "keywords": ["refactor", "rewrite", "clean up", "improve code", "restructure", "optimize", "simplify", "modernize"],
            "weight": 1.2
        },
        TaskType.QUICK_FIX: {
            "keywords": ["quick", "fast", "simple fix", "minor", "small change", "typo", "one line"],
            "weight": 1.5
        },
        TaskType.IMPLEMENTATION: {
            "keywords": ["implement", "build", "create", "develop", "api", "rest", "service", "endpoint", "feature", "function", "module", "component"],
            "weight": 1.0
        },
    }

    # Complexity factors
    COMPLEXITY_FACTORS = {
        "unknowns": ["unknown", "unclear", "unsure", "not sure", "unfamiliar", "new technology"],
        "irreversibility": ["deploy", "production", "migration", "database schema", "breaking change", "critical path"],
        "novelty": ["new technology", "unfamiliar", "never done", "first time", "experimental"],
        "regulatory": ["compliance", "gdpr", "pci", "hipaa", "audit", "regulation", "legal"],
        "criticality": ["core", "critical path", "mission critical", "revenue", "customer facing", "sla"],
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self._compiled = {}
        for task_type, config in self.PATTERNS.items():
            # Case-insensitive word boundary matching
            pattern = r'\b(' + '|'.join(re.escape(kw) for kw in config["keywords"]) + r')\b'
            self._compiled[task_type] = (re.compile(pattern, re.IGNORECASE), config["weight"])

    def classify(self, description: str) -> TaskClassification:
        """Classify a task description."""
        desc_lower = description.lower()
        
        # Score each task type
        scores = {}
        matched_keywords = {}
        
        for task_type, (pattern, weight) in self._compiled.items():
            matches = pattern.findall(description)
            if matches:
                # Normalize matches to lowercase for comparison
                matches_lower = [m.lower() for m in matches]
                scores[task_type] = len(matches) * weight
                matched_keywords[task_type] = list(set(matches_lower))
            else:
                scores[task_type] = 0
                matched_keywords[task_type] = []

        # Find best match
        if max(scores.values()) == 0:
            best_type = TaskType.IMPLEMENTATION
            confidence = 0.3
        else:
            best_type = max(scores, key=scores.get)
            max_score = scores[best_type]
            total = sum(scores.values())
            confidence = min(0.95, max_score / max(total, 1))

        complexity = self.assess_complexity(description)

        return TaskClassification(
            task_type=best_type,
            confidence=confidence,
            complexity=complexity,
            keywords_matched=matched_keywords.get(best_type, []),
            reasoning=f"Premise: Task requires {best_type.value} approach. Evidence: Matched {len(matched_keywords.get(best_type, []))} keywords ({', '.join(matched_keywords.get(best_type, []))}). Inference: {best_type.value.capitalize()} pipeline recommended."
        )

    def assess_complexity(self, description: str) -> int:
        """Assess task complexity (0-100)."""
        factors = {}
        
        for factor, keywords in self.COMPLEXITY_FACTORS.items():
            count = sum(1 for kw in keywords if kw in description.lower())
            factors[factor] = min(count * 20, 80)  # Max 80 per factor

        # Base complexity
        base = 30
        
        # Add factor contributions
        for factor, value in factors.items():
            base += value

        # Cap at 100
        return min(base, 100)

    def get_pipeline_variant(self, complexity: int) -> str:
        """Determine pipeline variant based on complexity."""
        if complexity < 30:
            return "LITE"
        elif complexity < 60:
            return "STANDARD"
        else:
            return "FULL"
