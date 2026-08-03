---
name: pinia
description: "Manages global state in Vue 3 applications using Pinia with TypeScript, actions, getters, and plugins."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Pinia, Vue 3, store, defineStore, action, getter, state, composition API, options API, Vuex migration
  role: specialist
  scope: implementation
  output-format: code
  related-skills: vue-expert, test-master, frontend-ui-engineering, tailwind-css
---

# Pinia

Vue 3 state management: stores, actions, getters, plugins, TypeScript integration, and SSR support with Pinia.

## When to Use This Skill

- Managing global or shared state in Vue 3 applications
- Migrating from Vuex to Pinia for simpler, TypeScript-friendly stores
- Implementing cross-component state with reactive computed getters
- Building SSR-compatible state management with Nuxt 3 and Pinia
- Structuring complex application state with multiple modular stores

## Key Capabilities

- **Store Definition** — Create stores with `defineStore()` using either Options API (`state`, `getters`, `actions`) or Composition API (setup function with refs and functions)
- **Typed Getters** — Define computed, cached derived state with full TypeScript inference and access to other getters via `this`
- **Actions & Mutations** — Perform synchronous or asynchronous state changes through actions (no separate mutation concept unlike Vuex), with full devtools tracking
- **Plugins & Middleware** — Extend all stores with plugins for persistence (localStorage), logging, or cross-store communication via Pinia's plugin API
- **SSR & Nuxt 3** — Use Pinia with Nuxt 3's auto-imports and SSR hydration, ensuring the store state is serialized server-side and hydrated client-side
- **Devtools Integration** — Inspect state changes, action history, and time-travel debug with Vue Devtools built-in support

## Best Practices

- Prefer the Composition API (`setup()`) style for stores when you need to compose logic across multiple stores or use composables inside a store
- Keep stores focused on a single domain (user store, cart store, product store) rather than one global store with everything
- Use `storeToRefs()` when destructuring store properties to maintain reactivity — direct destructuring breaks the reactive link
- Call `useStore()` inside `setup()` or component `<script setup>`; avoid calling it in non-component files unless passing the pinia instance
- For Nuxt 3, configure `modules: ['@pinia/nuxt']` and use `defineStore` in auto-imported composables for seamless SSR
