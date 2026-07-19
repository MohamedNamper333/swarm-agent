---
name: next-auth
description: Configures NextAuth.js/Auth.js for authentication in Next.js applications with multiple providers and adapters.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: authentication
  triggers: NextAuth, Auth.js, NextAuth.js, OAuth, credentials, adapter, Prisma, Drizzle, callbacks, middleware, session, JWT
  role: specialist
  scope: implementation
  output-format: code
  related-skills: clerk, nextjs-developer, secure-code-guardian
---

# NextAuth.js / Auth.js

NextAuth.js (now Auth.js) is a flexible authentication library for Next.js that supports OAuth providers, credential-based login, database adapters, JWT or database sessions, and middleware-based route protection. It provides a unified API for sign-in, sign-out, session retrieval, and callback hooks.

## When to Use This Skill

- Setting up authentication in a Next.js App Router or Pages Router application from scratch
- Integrating OAuth providers such as Google, GitHub, Discord, or Apple with minimal configuration
- Implementing credentials-based auth (email/password) with database-backed user storage
- Adding database adapters for Prisma, Drizzle, Supabase, or MongoDB to persist users and accounts
- Protecting API routes, server actions, and pages via `getServerSession` or middleware

## Key Capabilities

- Multi-provider configuration — Define any number of OAuth and credentials providers in a single `auth.ts` file
- Adapter-based persistence — Use Prisma, Drizzle, Kysely, Supabase, or custom adapters to store users, accounts, and sessions
- Callback hooks — Intercept sign-in, JWT, and session events to add custom claims, audit logging, or validation
- Middleware protection — Export `auth` middleware to protect routes with matchers, redirect unauthenticated users, or check roles
- JWT and database sessions — Choose stateless JWT tokens or server-side database sessions depending on your scalability needs

## Best Practices

- Store `AUTH_SECRET` as a secure environment variable and rotate it in production deployments
- Use the JWT strategy for API-heavy apps (no DB lookup on every request) and database sessions when you need server-side revocation
- Always validate callbacks with TypeScript and wrap provider configurations in `try/catch` during setup to surface misconfiguration early
