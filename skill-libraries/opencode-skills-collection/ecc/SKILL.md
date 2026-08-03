---
name: ecc
description: "ECC (Enterprise Coding Companion) — cross-harness agent OS for orchestrating multi-agent workflows, skills, plugins, and MCP servers across Claude Code, Cursor, Trae, and other coding harnesses. Use for agent harness orchestration, cross-harness workflow management, ECC tooling, and agentic operating system patterns."
swarm-worker: innovator
model-hint: deepseek-v4-flash-free|nemotron-3-ultra-free
---

# ECC — Agent Harness Operating System

ECC is the first cross-harness agent operating system. It unifies agent workflows, skills, plugins, and MCP configurations across Claude Code, Cursor, Trae, Cline, Windsurf, and other coding harnesses.

## Core Capabilities

- Cross-harness orchestration of agent workflows
- Unified skill registry and management
- MCP server configuration and management
- Plugin ecosystem with versioning and dependencies
- Agent evaluation and benchmarking
- Cost tracking and budget management
- Security scanning and compliance
- Automated CI/CD for agent workflows

## Architecture

ECC follows a modular architecture with:
- **Core engine** (`src/`) — orchestration, execution, and state management
- **Skills** (`skills/`) — 400+ reusable agent capabilities
- **Plugins** (`plugins/`) — extensible service integrations
- **Agents** (`agents/`) — pre-configured agent personas
- **Workflows** (`workflows/`) — multi-step orchestration pipelines
- **MCP configs** (`mcp-configs/`) — cross-harness MCP server definitions

## Related Skills

- `autonomous-agent-harness` — self-directing agent loops
- `mcp-developer`, `mcp-server-patterns` — MCP server development
- `workflow-orchestrator` — multi-stage agent workflow coordination
- `multi-agent-coordinator` — parallel agent task distribution
- `agent-orchestrator` — agent sequencing and routing
