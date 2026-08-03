---
name: sentry
description: Use when integrating Sentry for error tracking, performance monitoring, source map uploads, and alerting in frontend and backend applications. Invoke for SDK initialization, capturing exceptions, breadcrumbs, performance transactions, release management, and configuring alert rules.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: observability
  triggers: Sentry, error tracking, crash reporting, performance monitoring, source maps, alerts, exception handling, SDK, breadcrumbs, release health, span, transaction, tracing
  role: specialist
  scope: implementation
  output-format: code
  related-skills: nextjs-developer, react-expert, nestjs-expert, monitoring-expert, observability-and-instrumentation
---

# Sentry

Sentry is an application performance and error tracking platform that provides real-time visibility into production errors, performance bottlenecks, and release health. It captures exceptions with full stack traces, user context, and breadcrumbs, and correlates errors with performance spans to help diagnose root causes.

## When to Use This Skill

- Initializing Sentry SDK in frontend (React, Next.js) and backend (Node.js, Python) applications
- Capturing errors, warnings, and custom events with enriched context and breadcrumbs
- Setting up performance monitoring with distributed tracing across services
- Uploading source maps for readable stack traces and configuring alert rules for critical errors

## Key Capabilities

- Initialize Sentry with framework-specific SDKs (`@sentry/nextjs`, `@sentry/react`, `@sentry/node`) and configure DSN, environment, and release tags
- Instrument performance transactions and spans to measure operation latency and identify slow code paths
- Upload source maps via `sentry-cli` or build plugins for deobfuscated stack traces in production
- Configure alert rules, issue ownership, and Slack/PagerDuty integrations for actionable notifications

## Best Practices

- Set the `release` field to your deployed git SHA or version tag to correlate errors with deployments
- Upload source maps in your CI/CD pipeline and set `stripPrefix` to match your server paths
- Use `Sentry.configureScope` sparingly — prefer passing context directly to `captureException` for isolation
- Sample performance traces at a lower rate than error events (e.g., 0.1-0.2 `tracesSampleRate`) to manage quota

## Core Workflow

1. **Initialize** — Set up the Sentry SDK in your application entry point with DSN and environment
2. **Capture** — Errors are automatically captured; add manual `captureException` for caught exceptions
3. **Trace** — Instrument key operations with `Sentry.startTransaction` or auto-instrumentation
4. **Map** — Upload source maps during CI so production stack traces are readable
5. **Alert** — Configure alert rules in Sentry dashboard for error spikes and performance regressions

## Key Patterns

```typescript
// Next.js Sentry initialization
// sentry.client.config.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA,
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [Sentry.replayIntegration()],
});
```

```typescript
// Manual error capture with context
import * as Sentry from '@sentry/nextjs';

try {
  await processPayment(orderId, amount);
} catch (error) {
  Sentry.captureException(error, {
    tags: { orderId },
    extra: { amount, userId: currentUser.id },
    level: 'error',
  });
}
```

## Constraints

### MUST DO
- Set `environment` and `release` on every SDK init to distinguish environments and deployments
- Upload source maps in CI — never deploy without them in production
- Use `tracesSampleRate` ≤ 0.2 in production to stay within quota and reduce overhead

### MUST NOT DO
- Expose your Sentry DSN publicly for a self-hosted instance (it's safe for SaaS, but avoid on-prem)
- Capture sensitive user data (passwords, tokens, PII) in breadcrumbs or extra context
- Set `tracesSampleRate` to 1.0 in production — this will rapidly consume quota
