---
name: qwik
description: "Builds instant-loading Qwik applications with resumability, islands, and fine-grained lazy loading."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Qwik, Qwik City, resumability, $(), component$, useSignal, useStore, useResource$, lazy loading, island, DX, Optimizer
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, frontend-ui-engineering, test-master
---

# Qwik / Qwik City

Build instant web apps with Qwik: resumability, lazy loading, islands architecture, `$()` serialization, and Qwik City.

## When to Use This Skill

- Building applications where instant startup time is critical (slow networks, low-power devices)
- Architecting complex SPAs that need near-zero JavaScript on initial load
- Implementing resumable applications that pause on the server and resume on the client
- Creating full-stack applications with Qwik City's routing, loaders, and actions
- Building islands of interactivity within predominantly static pages

## Key Capabilities

- **Resumability Over Hydration** — Unlike traditional SSR that replays all JS on load, Qwik pauses execution on the server and resumes on the client only for the specific interactions the user triggers
- **Fine-Grained Lazy Loading** — Every component, listener, and effect is automatically code-split at the `$()` boundary; only the code needed for the current interaction is downloaded
- **`$()` Serialization** — Use the `$()` suffix to create lazily-loadable boundaries around closures allowing Qwik to serialize and revive functions across the network
- **Qwik City Routing** — Full-featured framework with file-based routing, loaders (`routeLoader$`), actions (`routeAction$`), layout nesting, middleware, and endpoints
- **Islands Architecture** — Combine static HTML with interactive islands; Qwik tracks which parts of the page the user interacts with and loads only that code
- **Optimizer** — Qwik's build-time optimizer analyzes code, applies transformations, and splits bundles automatically without manual configuration

## Best Practices

- Always suffix reactive primitives and event handlers with `$` (`useSignal()`, `component$()`, `$()`) to ensure the optimizer can properly code-split
- Prefer `useResource$()` for data fetching that should run on both server and client with serializable results
- Keep `$()` closures small and focused — their boundaries define code-split chunks, so large closures defeat lazy loading
- Use `useVisibleTask$()` sparingly (only for truly client-only imperative work); prefer `useResource$()` or `routeLoader$()` for data
- Understand the serialization rules — `$()` closures must only close over serializable values (no DOM references, no Map/Set without transformers)
