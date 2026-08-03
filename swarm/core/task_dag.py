"""
Task DAG Builder - Dynamic pipeline construction based on task classification
"""
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from copy import deepcopy

from .task_classifier import TaskClassifier, TaskType


@dataclass
class StageConfig:
    name: str
    min_time: int  # seconds
    workers: List[str]
    description: str
    outputs: List[str]
    constitutional_checks: List[str]
    order: int = 0
    depends_on: List[str] = field(default_factory=list)
    can_parallelize: bool = False


@dataclass
class DAGNode:
    name: str
    config: StageConfig
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class DAG:
    """Directed Acyclic Graph for task execution."""

    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
        self.edges: List[tuple] = []  # (from, to, edge_type)

    def add_node(self, name: str, config: StageConfig):
        self.nodes[name] = DAGNode(name=name, config=config)

    def add_edge(self, from_stage: str, to_stage: str, edge_type: str = "sequential"):
        self.edges.append((from_stage, to_stage, edge_type))

    def get_execution_order(self) -> List[str]:
        """Get topological order for execution."""
        visited = set()
        order = []
        temp_mark = set()

        def visit(stage: str):
            if stage in temp_mark:
                raise ValueError(f"Cycle detected at {stage}")
            if stage in visited:
                return
            temp_mark.add(stage)
            
            # Visit dependencies first
            for edge in self.edges:
                if edge[1] == stage and edge[2] == "sequential":
                    visit(edge[0])
            
            temp_mark.remove(stage)
            visited.add(stage)
            order.append(stage)

        for stage in self.nodes:
            if stage not in visited:
                visit(stage)
        
        return order

    def get_parallel_groups(self) -> List[List[str]]:
        """Get groups of stages that can run in parallel."""
        order = self.get_execution_order()
        groups = []
        current_group = []
        
        for stage_name in order:
            node = self.nodes[stage_name]
            deps = [e[0] for e in self.edges if e[1] == stage_name and e[2] == "sequential"]
            
            if not deps or all(d in [n.name for n in current_group] for d in deps):
                # Can run in current group
                current_group.append(node)
            else:
                # Need new group
                if current_group:
                    groups.append([n.name for n in current_group])
                current_group = [node]
        
        if current_group:
            groups.append([n.name for n in current_group])
        
        return groups

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram."""
        lines = ["flowchart TD"]
        for edge in self.edges:
            edge_style = "==>" if edge[2] == "sequential" else "-->"
            lines.append(f"    {edge[0]} {edge_style} {edge[1]}")
        return "\n".join(lines)


class DAGBuilder:
    """Builds dynamic execution DAG based on task classification."""

    STAGE_LIBRARY = {
        "analyze": StageConfig(
            name="analyze",
            min_time=60,
            workers=["explorer", "reasoner"],
            description="Understand the problem, research, identify unknowns",
            outputs=["research_report.md", "unknowns_map.md"],
            constitutional_checks=["EVIDENCE_OVER_AUTHORITY"]
        ),
        "ideate": StageConfig(
            name="ideate",
            min_time=120,
            workers=["innovator"],
            description="Generate creative solutions, first principles thinking",
            outputs=["ideas_list.md", "selected_approach.md"],
            constitutional_checks=["MINIMAL_SURFACE_AREA"]
        ),
        "design": StageConfig(
            name="design",
            min_time=180,
            workers=["architect", "reviewer"],
            description="Architecture design, API contracts, data flow",
            outputs=["design_spec.md", "api_contracts.md"],
            constitutional_checks=["REVERSIBILITY_BY_DEFAULT", "MINIMAL_SURFACE_AREA"]
        ),
        "implement": StageConfig(
            name="implement",
            min_time=300,
            workers=["architect", "vision-coder"],
            description="Write code, build components, integrate",
            outputs=["code_files", "tests"],
            constitutional_checks=["MINIMAL_SURFACE_AREA", "REVERSIBILITY_BY_DEFAULT"]
        ),
        "review": StageConfig(
            name="review",
            min_time=120,
            workers=["critic", "reviewer"],
            description="Code review, security audit, UX review",
            outputs=["review_report.md", "fixes_list.md"],
            constitutional_checks=["HONESTY_OVER_HELPFULNESS", "EVIDENCE_OVER_AUTHORITY"]
        ),
        "test": StageConfig(
            name="test",
            min_time=180,
            workers=["swarm-worker-qa"],
            description="Run tests, verify correctness, edge cases",
            outputs=["test_results.json", "coverage_report.md"],
            constitutional_checks=["HONESTY_OVER_HELPFULNESS"]
        ),
        "security_audit": StageConfig(
            name="security_audit",
            min_time=120,
            workers=["critic", "reasoner"],
            description="Security analysis, threat modeling, vulnerability scan",
            outputs=["security_report.md", "threat_model.md"],
            constitutional_checks=["HONESTY_OVER_HELPFULNESS", "EVIDENCE_OVER_AUTHORITY"]
        ),
        "optimize": StageConfig(
            name="optimize",
            min_time=120,
            workers=["architect", "reasoner"],
            description="Performance optimization, algorithmic improvements",
            outputs=["optimization_report.md", "benchmarks.json"],
            constitutional_checks=["MINIMAL_SURFACE_AREA"]
        ),
        "document": StageConfig(
            name="document",
            min_time=60,
            workers=["reviewer"],
            description="Write documentation, examples, API docs",
            outputs=["documentation.md", "examples/"],
            constitutional_checks=["HUMAN_AGENCY_PRESERVATION"]
        ),
        "verify": StageConfig(
            name="verify",
            min_time=90,
            workers=["reasoner", "swarm-worker-qa"],
            description="Final verification, auto-verdict, constitutional check",
            outputs=["quality_report.md", "verdict.json"],
            constitutional_checks=["ALL_FIVE"]
        ),
        "handoff": StageConfig(
            name="handoff",
            min_time=30,
            workers=["swarm"],
            description="Package results, write to vault, notify user",
            outputs=["handoff_package.md"],
            constitutional_checks=["HUMAN_AGENCY_PRESERVATION"]
        ),
    }

    TASK_TEMPLATES = {
        "creative": {
            "stages": ["analyze", "ideate", "design", "review", "verify", "handoff"],
            "primary_workers": ["innovator", "explorer", "reviewer"],
            "typical_duration": "30-60 min"
        },
        "security": {
            "stages": ["analyze", "design", "security_audit", "implement", "test", "verify", "handoff"],
            "primary_workers": ["critic", "reasoner", "architect"],
            "typical_duration": "60-120 min"
        },
        "research": {
            "stages": ["analyze", "ideate", "document", "verify", "handoff"],
            "primary_workers": ["explorer", "innovator", "reviewer"],
            "typical_duration": "20-40 min"
        },
        "implementation": {
            "stages": ["analyze", "design", "implement", "review", "test", "optimize", "verify", "handoff"],
            "primary_workers": ["architect", "critic", "swarm-worker-qa"],
            "typical_duration": "60-120 min"
        },
        "debug": {
            "stages": ["analyze", "implement", "test", "verify", "handoff"],
            "primary_workers": ["architect", "swarm-worker-qa", "reasoner"],
            "typical_duration": "15-30 min"
        },
        "refactor": {
            "stages": ["analyze", "design", "implement", "review", "test", "handoff"],
            "primary_workers": ["architect", "critic", "swarm-worker-qa"],
            "typical_duration": "30-60 min"
        },
        "quick_fix": {
            "stages": ["analyze", "implement", "verify", "handoff"],
            "primary_workers": ["architect", "swarm-worker-qa"],
            "typical_duration": "5-15 min"
        }
    }

    def __init__(self, classifier: Optional[TaskClassifier] = None):
        self.classifier = classifier or TaskClassifier()

    def build(self, task_description: str) -> DAG:
        """Build DAG for a task."""
        classification = self.classifier.classify(task_description)
        task_type = classification.task_type.value
        complexity = classification.complexity

        template = self.TASK_TEMPLATES.get(task_type, self.TASK_TEMPLATES["implementation"])
        stages = self._prune_stages(template["stages"], complexity)

        dag = DAG()
        for i, stage_name in enumerate(stages):
            stage_config = deepcopy(self.STAGE_LIBRARY[stage_name])
            stage_config.order = i
            stage_config.depends_on = [stages[i-1]] if i > 0 else []
            dag.add_node(stage_name, stage_config)

        # Add edges
        for i in range(1, len(stages)):
            dag.add_edge(stages[i-1], stages[i], "sequential")

        # Add parallel optimization hints
        dag = self._optimize_parallelism(dag)
        
        return dag

    def _prune_stages(self, stages: List[str], complexity: int) -> List[str]:
        """Prune stages based on complexity."""
        if complexity < 20:
            return ["analyze", "implement", "verify", "handoff"]
        elif complexity < 40:
            return [s for s in stages if s not in ["optimize", "document", "security_audit"]]
        elif complexity < 70:
            return [s for s in stages if s != "optimize"]
        return stages

    def _optimize_parallelism(self, dag: DAG) -> DAG:
        """Mark stages that can run in parallel."""
        # For now, mark independent stages as parallelizable
        # In future, analyze dependencies more deeply
        return dag

    def get_template_info(self, task_type: str) -> Dict:
        """Get information about a task template."""
        if task_type in self.TASK_TEMPLATES:
            template = self.TASK_TEMPLATES[task_type]
            return {
                "stages": template["stages"],
                "primary_workers": template["primary_workers"],
                "typical_duration": template["typical_duration"]
            }
        return {}

    def list_all_stages(self) -> List[str]:
        """List all available stage names."""
        return list(self.STAGE_LIBRARY.keys())
