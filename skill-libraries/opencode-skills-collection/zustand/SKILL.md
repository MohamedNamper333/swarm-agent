---
name: zustand
description: "Manages application state using Zustand stores with TypeScript, middleware, and slices pattern."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Zustand, store, state management, create, persist, devtools, middleware, slices, React, TypeScript
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, tanstack-query, test-master, frontend-ui-engineering
---

# Zustand

Lightweight state management for React/TS: stores, actions, selectors, middleware (persist, devtools), and slices pattern.

## When to Use This Skill

- Managing global or shared state in React applications without boilerplate
- Replacing Redux with a minimal, hook-based state management solution
- Persisting state to localStorage/AsyncStorage with automatic serialization
- Structuring large state objects using the slices pattern for better organization
- Debugging state changes with Redux DevTools integration via middleware

## Key Capabilities

- **Store Creation** — Define stores with `create()` accepting a function that returns state and actions, with no Provider wrapper needed
- **Selectors & Derived State** — Subscribe to specific slices of state with `useStore(state => state.part)` for optimal re-render performance
- **Actions as Functions** — Encapsulate mutations directly in the store as plain functions that use `set()` for immutable updates and `get()` for current state
- **Middleware** — Extend stores with built-in middleware: `persist` (localStorage, AsyncStorage), `devtools` (Redux DevTools), `immer` (mutable syntax), `subscribeWithSelector`
- **Slices Pattern** — Split large stores into modular slices functions that receive `set`, `get`, and `api` and are combined into one store
- **React Integration** — Access stores from any component with `useStore` hooks, including custom equality functions and selector-based subscriptions

## Best Practices

- Keep stores flat and minimal — split unrelated state into separate stores instead of one monolithic store to prevent unnecessary re-renders
- Define selectors outside components (or use `useShallow`) to avoid creating new references on every render
- Use the `persist` middleware with partialize to whitelist/blacklist specific fields from storage, excluding transient or computed state
- Leverage the `subscribe` API (outside React) for state-change side effects like analytics events or sync to external systems
- Type stores fully with TypeScript — the `StateCreator` utility type helps type the slices pattern correctly
