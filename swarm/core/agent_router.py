"""
Agent Router - Dynamic task routing to appropriate workers
"""
from typing import Dict, List, Optional
from .model_registry import ModelRegistry
from .task_classifier import TaskClassifier


class AgentRouter:
    """Routes tasks to the most appropriate agent based on task type and model availability."""

    ROUTING_TABLE = {
        "creative": ["innovator", "explorer", "reviewer"],
        "security": ["critic", "reasoner", "architect"],
        "research": ["explorer", "innovator", "reviewer"],
        "implementation": ["architect", "critic", "swarm-worker-qa"],
        "debug": ["architect", "swarm-worker-qa", "reasoner"],
        "refactor": ["architect", "critic", "swarm-worker-qa"],
        "quick_fix": ["architect", "swarm-worker-qa"],
    }

    WORKER_SPECIALIZATION = {
        "innovator": ["creative", "brainstorm", "ideate", "first_principles"],
        "critic": ["security", "review", "audit", "vulnerability", "code_review"],
        "architect": ["implementation", "coding", "design", "architecture", "infrastructure"],
        "explorer": ["research", "explore", "discover", "web_search", "fact_check"],
        "reviewer": ["review", "ux", "design", "documentation", "usability"],
        "reasoner": ["logic", "reason", "verify", "math", "formal_verification"],
        "vision-coder": ["vision", "multimodal", "image_analysis", "visual_tasks"],
        "laguna-s-2-1": ["general", "diverse_tasks", "fallback"],
        "ling-3-0-flash": ["fast_reasoning", "quick_tasks", "fallback"],
        "swarm-worker-qa": ["test", "qa", "verify", "testing", "validation"],
    }

    def __init__(self, model_registry: Optional[ModelRegistry] = None):
        self.model_registry = model_registry or ModelRegistry()
        self.classifier = TaskClassifier()

    def route(self, task_description: str) -> Dict:
        """Determine the best agent(s) for a task."""
        task_type = self.classifier.classify(task_description)
        complexity = self.classifier.assess_complexity(task_description)
        candidates = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["implementation"])

        # Filter by model health
        healthy = [w for w in candidates if self.model_registry.is_healthy(w)]

        if not healthy:
            healthy = candidates  # Fallback to all if none healthy

        return {
            "task_type": task_type,
            "complexity": complexity,
            "primary_workers": healthy[:3],  # Top 3
            "fallback_workers": [w for w in candidates if w not in healthy[:3]],
            "routing_reason": f"Task classified as {task_type} (complexity: {complexity})"
        }

    def get_specialization(self, worker: str) -> List[str]:
        """Get worker's specialization areas."""
        return self.WORKER_SPECIALIZATION.get(worker, [])
