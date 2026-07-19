---
name: dev-containers
description: "Configures development containers (devcontainers) for VS Code with tools, extensions, and port forwarding."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: devops
  triggers: devcontainer, dev container, devcontainer.json, development container, VS Code Remote, GitHub Codespaces, remote development
  role: specialist
  scope: implementation
  output-format: code
  related-skills: docker-compose, devops-engineer, python-pro, nodejs, context-engineering
---

# Dev Containers

Development container specialist — configures reproducible development environments using `devcontainer.json`, Dockerfiles, Dev Container Features, VS Code extension presets, post-create commands, and port forwarding for consistent team-wide workspaces and GitHub Codespaces.

## When to Use This Skill

- Creating a standardized development environment for a team that works across different OS platforms
- Setting up a GitHub Codespace with pre-installed languages, tools, VS Code extensions, and Dotfiles
- Configuring a project-specific devcontainer with database, cache, or API service dependencies alongside the development container
- Defining lifecycle scripts (postCreateCommand, postStartCommand) that automate environment setup (npm install, database migration, seed data)
- Containerizing an existing development workflow to eliminate "works on my machine" issues

## Key Capabilities

- Write `devcontainer.json` with image or Dockerfile reference, Features, extensions, settings, forwarded ports, mounts, remote user, and container environment variables
- Use Dev Container Features (`ghcr.io/devcontainers/features/*`) for quick installation of languages, runtimes (Node, Python, Go, Java, Rust, Ruby), and tools (Docker-in-Docker, Git, GitHub CLI, Terraform, kubectl)
- Configure VS Code settings per project (`settings.json` inside devcontainer) — enable/disable extensions, set editor preferences, configure formatters and linters
- Define lifecycle hooks — `onCreateCommand`, `postCreateCommand`, `postStartCommand`, `postAttachCommand` — for dependency installation, initial build, database migration, and post-setup tasks
- Set up forwarded ports from container to host with auto-labeling for dev server, database client UI, and preview URLs

## Best Practices

- Prefer Dev Container Features over custom Dockerfile commands for installing common tools — Features are versioned, cached, and tested across architectures
- Keep the devcontainer minimal for fast build times: use a slim base image and build only what is needed, deferring optional tooling to postCreateCommand
- Mount the workspace as a named volume instead of bind-mount (when possible) on macOS/Windows for better filesystem performance, or use the `target` with `workspaceMount` for custom layouts
