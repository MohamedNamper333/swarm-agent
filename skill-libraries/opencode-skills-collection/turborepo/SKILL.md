---
name: turborepo
description: Configures and manages monorepos using Turborepo with task scheduling, caching, and dependency graphs.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: build-tooling
  triggers: Turborepo, monorepo, turbo, pipeline, remote caching, task orchestration, dependency graph
  role: specialist
  scope: implementation
  output-format: code
  related-skills: nx, nextjs-developer, ci-cd-and-automation
---

# Turborepo

Turborepo is a high-performance monorepo build system that uses incremental task execution, content-aware caching (local and remote), parallel orchestration, and dependency graph analysis. It works with any package manager (npm, pnpm, yarn) and integrates seamlessly with Next.js and other framework-based projects.

## When to Use This Skill

- Setting up a monorepo with Turborepo for a multi-package JavaScript/TypeScript project
- Configuring `turbo.json` pipelines for build, lint, test, and dev tasks with dependency ordering
- Enabling remote caching on Vercel or S3 to share build artifacts across CI and developer machines
- Optimizing CI pipelines by parallelizing tasks across packages and caching unchanged outputs
- Migrating an existing monorepo from Lerna, Nx, or pnpm workspaces to Turborepo

## Key Capabilities

- Pipeline configuration — Define task dependencies (`dependsOn`), output globs, environment variable inputs, and concurrency limits in `turbo.json`
- Content-aware caching — Hash task inputs (source files, deps, env vars) and skip tasks whose cache is still warm; share cache via remote caching
- Parallel execution — Run independent package tasks concurrently with a configurable `--concurrency` limit
- Dependency graph visualization — Use `turbo run build --graph` to output a Graphviz-compatible graph of inter-package task dependencies
- Scope and filters — Run tasks only for affected packages (`--filter=...`) based on git changes since a base branch

## Best Practices

- Define explicit `outputs` for each task so Turborepo can prune stale caches; omit outputs for side-effect tasks like lint
- Cache env vars explicitly in `turbo.json` under each task's `env` list to prevent incorrect "cache hit" across different environments
- Pin the Turborepo version across the team using the `turbo` installation in `package.json` to avoid cache-invalidation mismatches
