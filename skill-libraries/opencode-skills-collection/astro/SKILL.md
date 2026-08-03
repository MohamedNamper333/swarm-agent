---
name: astro
description: "Builds content-focused Astro websites with islands architecture, multiple UI framework support (React/Vue/Svelte), and content collections."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Astro, .astro, island, content collection, Astro DB, view transition, Markdown, MDX, SSG, static site, server island
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, frontend-ui-engineering, test-master, svelte, react-expert
---

# Astro

Build performant content websites with Astro's island architecture, `.astro` components, content collections, and multi-framework integration.

## When to Use This Skill

- Building content-focused websites (blogs, docs, marketing sites, e-commerce)
- Architecting zero-JS-by-default pages with selective framework islands
- Integrating multiple UI frameworks (React, Vue, Svelte) in a single project
- Managing structured content with Astro's content collections and schemas
- Building dynamic pages with server islands, Astro DB, or view transitions

## Key Capabilities

- **Islands Architecture** — Ship zero JavaScript by default and selectively hydrate interactive components using `client:load`, `client:idle`, `client:visible`, and `client:media`
- **Content Collections** — Define typed content schemas with Zod, manage Markdown/MDX collections, and query them with type-safe APIs
- **Multi-Framework Support** — Use React, Vue, Svelte, Solid, Preact, or Lit components side-by-side within the same Astro project
- **SSG, SSR & Server Islands** — Generate static HTML at build time, render on-demand with SSR adapters, or mix both via server islands for dynamic content
- **Built-in Optimizations** — Automatic image optimization, CSS/JS bundling, partial hydration, view transitions API, and asset pipeline
- **Astro Integrations** — Extend with official integrations for Tailwind, MDX, Sitemap, RSS, Partytown, and framework adapters (Netlify, Vercel, Cloudflare, Node)

## Best Practices

- Default to `.astro` components (zero JS) and only add interactive framework islands where user interaction is required
- Define Zod schemas for all content collections to get full type safety and validation at build time
- Use `content/` collections for structured content and reserve `src/pages/` for route-defined pages
- Prefer server islands over API calls for dynamic data to reduce client-side JavaScript
- Use Astro's built-in image optimization (`<Image />`, `<Picture />`) instead of manual img tags
