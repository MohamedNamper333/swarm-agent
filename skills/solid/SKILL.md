---
name: solid
description: "Builds reactive SolidJS applications with Signals, Stores, and fine-grained reactivity patterns."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: SolidJS, Solid, JSX, Signal, createSignal, createEffect, createMemo, createResource, createStore, Store, SolidStart, fine-grained reactivity
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, frontend-ui-engineering, test-master, designing-frontend-interfaces
---

# SolidJS

Build reactive UIs with SolidJS: Signals, Effects, Memos, Stores, resource management, and SSR with SolidStart.

## When to Use This Skill

- Building highly reactive UIs with fine-grained reactivity and minimal re-renders
- Creating performant web applications where avoiding virtual DOM overhead is critical
- Implementing complex state management with Signals and Stores
- Building full-stack apps with SolidStart SSR, routing, and server functions
- Developing reusable component libraries with Solid's JSX-based composable API

## Key Capabilities

- **Signals & Reactivity** — Manage local state with `createSignal()` for read/write pairs that trigger precise DOM updates without a virtual DOM
- **Derived State & Memos** — Compute derived values efficiently with `createMemo()` that only re-evaluates when its dependencies change
- **Stores for Nested State** — Handle deep reactive objects with `createStore()` and `produce`-style immutable updates for arrays and nested data
- **Resource Management** — Fetch async data declaratively with `createResource()` including refetching, suspense integration, and error handling
- **Effects & Lifecycle** — Run side-effects reactively with `createEffect()` and manage component lifecycle with `onMount()`, `onCleanup()`, and `onError()`
- **SolidStart SSR** — Build full-stack applications with SolidStart including file-based routing, server functions, streaming, and island hydration

## Best Practices

- Keep signals granular — create separate signals for independent pieces of state rather than lumping everything into a store
- Use `createMemo()` for expensive computations and `createEffect()` only for side effects (not for deriving state)
- Prefer `createStore()` over arrays of signals when dealing with lists or nested objects to maintain reactivity
- Always pair `createResource` with `<Suspense>` or `<ErrorBoundary>` for loading and error states
- Avoid destructuring signals (`const [count, setCount] = createSignal(0)`); pass `count()` as a function to preserve reactivity across component boundaries
