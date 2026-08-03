---
name: vercel-deploy
description: "Configures and deploys projects to Vercel with preview deployments, environment variables, and serverless functions."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: devops
  triggers: Vercel, deploy, deployment, preview deployment, vercel.json, Vercel Edge Functions, Vercel Analytics, hosting, CI/CD
  role: specialist
  scope: implementation
  output-format: code
  related-skills: nextjs-developer, serverless, github-actions, frontend-ui-engineering, monitoring-expert
---

# Vercel Deployment

Vercel deployment specialist — configures project deployment, preview environments, environment variables, serverless and edge functions, analytics, and CI/CD integration using `vercel.json`, CLI, and GitHub/GitLab/Bitbucket integration.

## When to Use This Skill

- Configuring a new Vercel project for a Next.js, SvelteKit, Astro, Remix, or static site
- Setting up preview deployments for pull requests with environment variable overrides and branch-specific settings
- Writing `vercel.json` for rewrites, redirects, headers, internationalization, and function region configuration
- Deploying serverless and edge functions with custom routing, middleware, and ISR (Incremental Static Regeneration)
- Integrating Vercel Analytics, Speed Insights, and Log Drains for production observability

## Key Capabilities

- Configure `vercel.json` — rewrites, redirects, headers, trailing slash, `cleanUrls`, `regions`, `framework`, `buildCommand`, `outputDirectory`, `installCommand`, and `functions` resource overrides
- Manage environment variables across teams, projects, and preview/production scopes using the Vercel dashboard, CLI (`vc env`), or `vercel.json` `env` block
- Deploy serverless and edge functions — define function routes in `api/` or `vercel.json`, set memory/timeout, and choose regions (iad1, hkg1, gru1, etc.)
- Configure Incremental Static Regeneration (ISR) with `revalidate` and On-Demand Revalidation via API route for hybrid static + dynamic pages
- Enable preview deployments — automatic per-PR deployments with unique URLs, password protection, and environment variable inheritance

## Best Practices

- Use `vc env pull` to sync remote environment variables to `.env.local` for local development parity with production
- Set `framework` explicitly in `vercel.json` to ensure correct build command detection and output directory resolution
- Add `"regions": ["iad1"]` or similar on performance-critical functions and ISR pages to pin them to a single region, avoiding cold-start latency from regional fan-out
