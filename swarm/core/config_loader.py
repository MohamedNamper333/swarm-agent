"""
Config Loader - Load dynamic agent configurations
"""
import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    id: str
    name: str
    role: str
    description: str
    model: str
    candidate_models: List[Dict] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    tools: Dict[str, bool] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    specialization: List[str] = field(default_factory=list)
    scratchpad_template: str = ""


class ConfigLoader:
    """Load and manage dynamic agent configurations."""

    DEFAULT_CONFIG_PATH = "opencode.json"
    TEMPLATE_DIR = "templates"

    def __init__(self, config_path: str = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.agents: Dict[str, AgentConfig] = {}
        self.pipeline_templates: Dict[str, List[str]] = {}
        self.tools: Dict[str, Dict] = {}

    def load(self) -> bool:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            self._parse_agents()
            self._parse_pipeline_templates()
            self._parse_tools()
            return True
        except Exception as e:
            print(f"Failed to load config: {e}")
            return False

    def _parse_agents(self):
        """Parse agent definitions from config."""
        agents = self.config.get("agent", {})
        for agent_id, agent_data in agents.items():
            self.agents[agent_id] = AgentConfig(
                id=agent_id,
                name=agent_data.get("name", agent_id),
                role=agent_data.get("role", ""),
                description=agent_data.get("description", ""),
                model=agent_data.get("model", ""),
                candidate_models=agent_data.get("candidate_models", []),
                skills=agent_data.get("skills", []),
                tools=agent_data.get("tools", {}),
                permissions=agent_data.get("permission", {}),
                specialization=agent_data.get("specialization", []),
                scratchpad_template=agent_data.get("scratchpad_template", "")
            )

    def _parse_pipeline_templates(self):
        """Parse pipeline templates from config."""
        self.pipeline_templates = self.config.get("pipeline_templates", {})

    def _parse_tools(self):
        """Parse tool definitions."""
        self.tools = self.config.get("tools", {})

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID."""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations."""
        return self.agents

    def get_worker_agents(self) -> Dict[str, AgentConfig]:
        """Get only worker agents (not coordinator)."""
        return {k: v for k, v in self.agents.items() if v.id != "swarm"}

    def get_coordinator(self) -> Optional[AgentConfig]:
        """Get coordinator configuration."""
        return self.agents.get("swarm")

    def get_pipeline_template(self, task_type: str) -> List[str]:
        """Get pipeline stages for a task type."""
        return self.pipeline_templates.get(task_type, 
            ["analyze", "design", "implement", "review", "test", "verify", "handoff"])

    def get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Get tool definition by name."""
        return self.tools.get(tool_name)

    def get_dynamic_behavior(self) -> Dict:
        """Get dynamic behavior config."""
        return self.config.get("dynamic_behavior", {})

    def get_vault_config(self) -> Dict:
        """Get vault integration config."""
        return self.config.get("vault_integration", {})

    def get_observability_config(self) -> Dict:
        """Get observability config."""
        return self.config.get("observability", {})

    def save(self, path: str = None) -> bool:
        """Save configuration to file."""
        try:
            path = path or self.config_path
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False

    def validate_agent_config(self, agent_id: str) -> List[str]:
        """Validate agent configuration."""
        errors = []
        agent = self.agents.get(agent_id)
        if not agent:
            return [f"Agent {agent_id} not found"]

        if not agent.model:
            errors.append(f"Agent {agent_id} missing model")

        if not agent.skills:
            errors.append(f"Agent {agent_id} missing skills")

        # Check skills exist
        for skill in agent.skills:
            if not os.path.exists(f"skills/{skill}/SKILL.md"):
                errors.append(f"Skill {skill} not found for agent {agent_id}")

        return errors

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all agent configurations."""
        results = {}
        for agent_id in self.agents:
            errors = self.validate_agent_config(agent_id)
            if errors:
                results[agent_id] = errors
        return results

    def get_worker_specializations(self) -> Dict[str, List[str]]:
        """Get specialization mapping for routing."""
        return {
            agent_id: agent.specialization
            for agent_id, agent in self.agents.items()
            if agent_id != "swarm"
        }

    def get_model_assignments(self) -> Dict[str, str]:
        """Get primary model for each agent."""
        return {
            agent_id: agent.model
            for agent_id, agent in self.agents.items()
        }

    def reload(self) -> bool:
        """Reload configuration from disk."""
        return self.load()
