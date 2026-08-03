---
name: github-actions
description: "Creates CI/CD workflows with GitHub Actions including matrix builds, caching, deployment, and custom actions."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: devops
  triggers: GitHub Actions, CI/CD, workflow, GitHub workflow, action, continuous integration, continuous deployment, pipeline, GHA
  role: specialist
  scope: implementation
  output-format: code
  related-skills: vercel-deploy, devops-engineer, terraform-engineer, test-master, security-reviewer, docker-compose
---

# GitHub Actions

GitHub Actions CI/CD specialist — designs and implements workflow automation using GitHub Actions YAML syntax, matrix builds, caching, artifacts, secrets, deployment environments, reusable workflows, and custom composite/JavaScript/Docker actions.

## When to Use This Skill

- Setting up continuous integration (lint, type-check, test, build) on pull requests and pushes
- Configuring multi-platform matrix builds (OS, Node version, Python version, architecture) for library and application testing
- Implementing continuous deployment to Vercel, AWS, Docker Hub, or Kubernetes with environment gates and approval workflows
- Creating reusable workflows or custom actions to standardize CI across multiple repositories in an organization
- Automating release workflows — semantic versioning, changelog generation, GitHub Release creation, and package publishing

## Key Capabilities

- Write workflow YAML with triggers (`push`, `pull_request`, `workflow_dispatch`, `schedule`, `repository_dispatch`), job dependencies (`needs`), conditionals (`if`), and concurrency groups
- Configure matrix strategies (`strategy.matrix`) testing across versions, platforms, and configurations with `fail-fast` and `max-parallel` controls
- Implement caching for dependencies (npm, pip, Maven, Gradle, Docker layers) using `actions/cache` with proper key hashing and restore keys
- Build and publish custom actions: composite actions (YAML), JavaScript actions (with `@actions/core`), and Docker container actions
- Manage secrets and environments — store per-environment secrets, require reviewers for production deployments, and use OIDC for cloud provider authentication

## Best Practices

- Pin action versions to commit SHAs for third-party actions (`uses: actions/checkout@v4` is OK, but prefer `@<sha>` for actions outside `actions/` org) and use Dependabot for automated updates
- Keep workflows focused and composable — split CI/CD concerns into separate workflow files and use reusable workflows (`workflow_call`) to avoid duplication
- Always set `timeout-minutes` on jobs to prevent runaway workflows, and use `actions/upload-artifact` / `actions/download-artifact` for sharing outputs between jobs
