---
name: svelte
description: "Builds reactive Svelte 5+ and SvelteKit applications with runes, server-side rendering, form actions, and endpoint configuration."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Svelte, SvelteKit, runes, $state, $derived, $effect, SSR, form action, load function, +page.svelte, +page.server.js, +server.js
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, frontend-ui-engineering, test-master, designing-frontend-interfaces
---

# Svelte / SvelteKit

Build modern reactive web apps with Svelte 5+ runes ($state, $derived, $effect) and SvelteKit's full-stack features: SSR, load functions, form actions, hooks, and endpoints.

## When to Use This Skill

- Building reactive UIs with Svelte 5+ runes-based reactivity system
- Creating full-stack web applications with SvelteKit routing, SSR, and server endpoints
- Implementing form handling with SvelteKit form actions and progressive enhancement
- Setting up data loading patterns with SvelteKit load functions and invalidation
- Developing performant SPAs or static sites with Svelte's minimal bundle output

## Key Capabilities

- **Runes Reactivity** — Leverage Svelte 5 runes ($state, $derived, $effect, $props) for fine-grained reactive programming without the old `let` assignment model
- **SvelteKit Routing & Endpoints** — Configure file-based routing with +page, +layout, +server, and +error files, plus API endpoints via +server.js
- **Form Actions & Progressive Enhancement** — Implement use:enhance for client-side form handling with action functions and seamless JavaScript fallback
- **SSR & Load Functions** — Fetch data on the server with universal and server load functions, with automatic cache invalidation and streaming
- **Stores & State Management** — Manage shared state with Svelte's writable/readable stores, derived stores, and the new $state rune for local reactivity
- **Transitions & Animations** — Apply built-in transition directives (fade, slide, fly) and animation functions for declarative motion

## Best Practices

- Use runes ($state, $derived) for component-local reactivity in Svelte 5; reserve stores for truly shared cross-component state
- Prefer `+page.server.js` load functions for sensitive data that should never reach the client, and `+page.js` for public data
- Validate form actions server-side with structured error handling and return action data rather than throwing exceptions
- Leverage `invalidate()` and `invalidateAll()` judiciously to avoid over-fetching after mutations
- Keep `.svelte` files focused on template logic; extract business logic into standalone `.js`/`.ts` modules
