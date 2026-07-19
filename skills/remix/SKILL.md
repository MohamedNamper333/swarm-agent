---
name: remix
description: "Builds Remix-run web applications with nested routes, loaders, actions, and progressive enhancement patterns."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: fullstack
  triggers: Remix, Remix Run, loader, action, nested route, Outlet, Form, useFetcher, useLoaderData, useActionData, deferred, web standard, fetch
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, fullstack-guardian, test-master, react-expert
---

# Remix

Build full-stack web apps with Remix: nested routing, server-side loaders/actions, forms, error boundaries, and progressive enhancement.

## When to Use This Skill

- Building full-stack web applications that heavily use server-side rendering
- Architecting complex UIs with nested routing and shared layout data
- Implementing form workflows with progressive enhancement and validation
- Building data-driven pages where the server owns data fetching and mutations
- Creating web-standard applications using Fetch API, Request/Response, and Web Streams

## Key Capabilities

- **Nested Routing & Layouts** — Define routes as nested directory structures with shared layouts via `<Outlet />`, each route segment owning its data and UI
- **Server-Side Loaders & Actions** — Fetch data in `loader` functions and handle mutations in `action` functions, both running exclusively on the server
- **Progressive Enhancement** — Build `<Form>` components that work without JavaScript and automatically enhance when JS loads; use `useFetcher` for non-navigation mutations
- **Error & Catch Boundaries** — Handle rendering and data errors per route with `ErrorBoundary` and route-level `CatchBoundary` for granular fallback UI
- **Resource Routes** — Create non-UI endpoints (API, file downloads, webhooks) with `resource routes` that return any Response type
- **Deferred Data & Streaming** — Stream non-critical data with `defer()` and `<Await>` for faster initial page loads without blocking on slow data

## Best Practices

- Let the server own all data: fetch in `loader`, mutate in `action`, and never fetch on the client unless necessary for real-time updates
- Co-locate route modules with their components, loaders, and actions for clear ownership
- Use `useFetcher` instead of `<Form>` for mutations that don't navigate (add to cart, like, follow)
- Return proper HTTP status codes from actions (`400`, `401`, `422`) with structured error responses for robust form handling
- Leverage `defer()` to stream secondary data while critical data blocks the initial render
