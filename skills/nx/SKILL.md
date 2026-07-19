---
name: nx
description: Configures and manages monorepos using Nx with generators, executors, dependency graphs, and affected commands.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: build-tooling
  triggers: Nx, monorepo, workspace, generator, executor, affected, nx.json, dependency graph, caching
  role: specialist
  scope: implementation
  output-format: code
  related-skills: turborepo, nextjs-developer, ci-cd-and-automation, angular-architect
---

# Nx

Nx is a next-generation build system and monorepo toolkit that provides code generators, task executors, dependency graph analysis, affected-command detection, and distributed task execution (Nx Cloud). It supports Angular, React, Next.js, Node, NestJS, and many other frameworks through plugins.

## When to Use This Skill

- Scaffolding a new monorepo workspace with Nx for a team building multiple apps and shared libraries
- Creating reusable generators and executors to enforce project conventions and automate boilerplate
- Optimizing CI pipelines with Nx Cloud's distributed task execution and affected-command filtering
- Migrating an existing Angular or React project into an Nx-managed monorepo with workspace-level linting and testing
- Analyzing project dependencies and boundaries using the Nx dependency graph and module boundary rules

## Key Capabilities

- Workspace generators — Use `nx generate` to scaffold apps, libs, components, and features with framework-specific templates
- Executors and custom tooling — Build custom executors (Node scripts, shell commands) and configure them in `project.json` or `workspace.json`
- Affected commands — Run `nx affected:test`, `nx affected:build`, etc. to only execute tasks on projects that changed since a git base
- Dependency graph — Visualize project relationships with `nx graph` or `nx graph --focus=<project>` for debugging circular deps and boundary violations
- Enforced module boundaries — Define tags and constraints in `.eslintrc.json` or `nx.json` to prevent libraries from depending on forbidden layers

## Best Practices

- Keep `nx.json` as the single source of truth for cacheability, parallelism, and task runner configuration across the entire workspace
- Use `nx workspace-generator` to codify team conventions rather than copying boilerplate manually between projects
- Set up proper `targetDefaults` for `build`, `test`, `lint` so every project inherits sensible cache inputs and outputs without repeating configuration
