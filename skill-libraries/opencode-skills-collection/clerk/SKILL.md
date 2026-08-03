---
name: clerk
description: Integrates Clerk authentication and user management with React, Next.js, and other frameworks.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: authentication
  triggers: Clerk, auth, sign-in, sign-up, user management, organizations, session, middleware, webhooks
  role: specialist
  scope: implementation
  output-format: code
  related-skills: next-auth, nextjs-developer, secure-code-guardian
---

# Clerk

Clerk is a complete authentication and user management platform that provides pre-built React and Next.js components, session handling, organization management, and webhook integration. It supports multiple social login providers, multi-factor authentication, and customizable UI components with minimal boilerplate.

## When to Use This Skill

- Adding authentication to a Next.js or React application with Clerk's `<SignIn />` and `<SignUp />` components
- Implementing organization-based multi-tenancy with role-based access control
- Configuring session management, middleware protection, and API route authentication
- Syncing Clerk user data with an external database via webhook handlers
- Customizing the Clerk UI theme, fields, or flows to match brand requirements

## Key Capabilities

- Pre-built auth components — Drop in `<SignIn />`, `<SignUp />`, `<UserButton />`, and `<OrganizationSwitcher />` with zero styling effort
- Middleware-based route protection — Use `auth().protect()` in Next.js middleware to guard pages and API routes by role or permission
- Organization management — Create and manage orgs, invite members, assign roles (admin/member), and scope data per organization
- Webhook integration — Handle `user.created`, `user.updated`, `organization.*` events to sync Clerk data into a local database
- Session and user APIs — Access `currentUser()`, `auth()`, and `clerkClient` on server side for custom backend logic

## Best Practices

- Keep Clerk environment keys (`CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`) out of client bundles by using server-only helpers
- Use Clerk webhooks (not client-side triggers) to persist user data to your database for data consistency
- Always wrap pages that depend on auth data in `<ClerkLoading />` / `<ClerkLoaded />` or use `waitForInitialRender` to prevent flash of unauthenticated content
