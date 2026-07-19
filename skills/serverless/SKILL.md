---
name: serverless
description: "Builds and deploys serverless functions on AWS Lambda, Cloudflare Workers, and Vercel Edge Functions."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: backend
  triggers: serverless, Lambda, AWS Lambda, Cloudflare Workers, Vercel Edge Functions, edge compute, function-as-a-service, Faas, serverless function
  role: specialist
  scope: implementation
  output-format: code
  related-skills: vercel-deploy, terraform-engineer, devops-engineer, monitoring-expert, fullstack-guardian
---

# Serverless

Serverless compute specialist — designs, implements, and deploys serverless functions on AWS Lambda, Cloudflare Workers, and Vercel Edge Functions, covering handler patterns, cold start mitigation, environment configuration, triggers, and observability.

## When to Use This Skill

- Building REST API endpoints or webhook handlers as serverless functions on AWS Lambda (API Gateway, Function URL) or Vercel
- Writing Cloudflare Workers for edge-located request handling, A/B testing, redirects, or KV-backed APIs
- Implementing cron/scheduled triggers (EventBridge, Cloudflare Cron Triggers, Vercel Cron Jobs) for periodic batch processing
- Processing asynchronous event streams — SQS, SNS, DynamoDB Streams, Kinesis, or Cloudflare Queues
- Migrating an existing Express/Fastify app to a serverless architecture using Lambda Web Adapter or Vercel serverless functions

## Key Capabilities

- Write Lambda handlers with proper async/await, error handling, structured logging, and context object awareness (remaining time, request ID, cold start detection)
- Configure Cloudflare Workers with module syntax (`export default { async fetch(request, env, ctx) {} }`), Workers KV, D1, R2, Queues, and Cron Triggers
- Optimize cold starts — minimize bundle size, use only necessary dependencies, leverage Lambda snapstart (Java/.NET) or provisioned concurrency, and split functions by domain
- Manage environment variables and secrets per stage via platform tooling (AWS SSM / Secrets Manager, Cloudflare Secrets, Vercel Environment Variables)
- Instrument observability: structured JSON logging with correlation IDs, distributed tracing (AWS X-Ray, Cloudflare Tail Workers), and error alerting

## Best Practices

- Design functions to be stateless — store session, cache, and persistent data in external services (DynamoDB, KV, S3, D1); never rely on local function filesystem
- Keep function bundles small (under 1 MB compressed) by tree-shaking dependencies and using platform-native runtime features instead of SDK clients
- Set appropriate timeouts, memory sizes, and concurrency limits per function based on workload profile, and always implement idempotent handlers for event-driven invocations
