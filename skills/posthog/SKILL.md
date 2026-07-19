---
name: posthog
description: Use when integrating PostHog for product analytics, event tracking, feature flags, session recording, and experimentation. Invoke for SDK setup, custom event capture, user identification, feature flag evaluation, A/B testing, and funnel analysis configuration.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: analytics
  triggers: PostHog, product analytics, event tracking, feature flags, session recording, A/B testing, experiments, funnel analysis, cohort, user identification, heatmaps, autocapture, posthog-js
  role: specialist
  scope: implementation
  output-format: code
  related-skills: nextjs-developer, sentry, fullstack-guardian, business-analysis
---

# PostHog

PostHog is an open-source product analytics platform that combines event tracking, feature flags, session recording, and experimentation in a single tool. It provides self-hosted and cloud options with full control over user data, enabling teams to understand user behavior, ship features safely, and run A/B tests.

## When to Use This Skill

- Setting up PostHog SDK in frontend or backend applications with autocapture or custom events
- Implementing feature flags for gradual rollouts, kill switches, and beta programs
- Capturing custom events with properties for funnel and retention analysis
- Configuring session recordings and heatmaps for UX insights

## Key Capabilities

- Initialize `posthog-js` with autocapture, session recording, and user identification for comprehensive analytics
- Evaluate feature flags with multivariate support, rollout percentages, and user-specific overrides
- Track custom events with typed properties for building funnels, trends, and cohort analyses
- Run A/B experiments with statistical significance calculations and automated result reporting

## Best Practices

- Identify users with `posthog.identify` as early as possible to associate events with distinct user profiles
- Group related properties under a consistent naming convention (e.g., `$product_id`, `$plan_type`) for cleaner analysis
- Use feature flags with gradual rollouts (e.g., 5% → 25% → 100%) rather than hard cutovers
- Disable autocapture for sensitive input fields by adding the `data-ph-no-capture` attribute

## Core Workflow

1. **Init** — Install and configure `posthog-js` in your app with your project API key
2. **Identify** — Call `posthog.identify` when users sign in and `posthog.reset` on logout
3. **Track** — Fire custom events at key user actions with relevant properties
4. **Flag** — Implement feature flags to conditionally show or hide functionality
5. **Analyze** — Review funnels, trends, and session recordings in the PostHog dashboard

## Key Patterns

```typescript
// Next.js PostHog provider
'use client';
import { PostHogProvider } from 'posthog-js/react';
import posthog from 'posthog-js';

if (typeof window !== 'undefined') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
    capture_pageview: true,
    capture_pageleave: true,
    session_recording: { maskAllInputs: true },
    loaded: (ph) => {
      if (process.env.NODE_ENV !== 'production') ph.opt_out_capturing();
    },
  });
}

export function PHProvider({ children }: { children: React.ReactNode }) {
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}
```

```typescript
// Feature flag evaluation
const isEnabled = posthog.isFeatureEnabled('new-checkout-flow');

if (isEnabled) {
  // render new checkout
} else {
  // render legacy checkout
}

// Custom event with properties
posthog.capture('subscription_started', {
  plan: 'pro',
  price: 29,
  source: 'landing_page',
});
```

## Constraints

### MUST DO
- Call `posthog.identify` with a consistent distinct ID (usually the user's database ID)
- Mask sensitive inputs with `data-ph-no-capture` or `maskAllInputs: true` for session recording
- Include a way for users to opt out of analytics (GDPR compliance)

### MUST NOT DO
- Track personally identifiable information (PII) in event property names or values
- Bypass user consent mechanisms — check consent before initializing PostHog
- Evaluate feature flags on the server side without passing the `distinct_id` explicitly
