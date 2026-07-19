---
name: docker-compose
description: "Orchestrates multi-container Docker applications with Compose files, networking, volumes, and health checks."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: devops
  triggers: Docker Compose, docker-compose.yml, compose, multi-container, orchestration, Docker, container, service, docker compose
  role: specialist
  scope: implementation
  output-format: code
  related-skills: dev-containers, devops-engineer, github-actions, terraform-engineer, monitoring-expert
---

# Docker Compose

Docker Compose specialist — orchestrates multi-container Docker applications using Compose files, defining services, networks, volumes, health checks, environment variables, dependencies, and production overrides for local development and CI.

## When to Use This Skill

- Setting up a local development environment with multiple services (app, database, cache, queue, reverse proxy)
- Configuring a CI test environment that spins up ephemeral service dependencies (PostgreSQL, Redis, Kafka, MinIO)
- Defining production-like staging environments with resource limits, restart policies, and logging drivers
- Running integration or E2E tests against real service dependencies in an isolated Compose network
- Prototyping a microservices application architecture locally before Kubernetes migration

## Key Capabilities

- Write `docker-compose.yml` (v3.8+) with service definitions — image, build context, ports, volumes, environment, depends_on, healthcheck, restart, deploy, and resource reservations
- Configure custom networks — bridge (default), overlay (Swarm), MacVLAN, and IPAM — with service isolation, aliases, and static IPs
- Define named volumes with drivers (local, NFS, cloud) and bind mounts for persistent data and live code reloading
- Implement health checks using `curl`, `wget`, or custom commands with `interval`, `timeout`, `retries`, and `start_period` so dependent services wait for readiness
- Create Compose override files (`docker-compose.override.yml`, `docker-compose.prod.yml`) for environment-specific configuration using `-f` flag and `extends` / `profiles`

## Best Practices

- Always pin service image tags to specific versions (`postgres:16-alpine`) instead of `latest` to ensure reproducible builds
- Use `.env` files with variable substitution for secrets and stage-specific values — never hardcode credentials in `docker-compose.yml`
- Set `depends_on` with `condition: service_healthy` (not just `depends_on` alone) to guarantee service startup order when readiness matters
