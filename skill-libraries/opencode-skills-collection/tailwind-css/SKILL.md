---
name: tailwind-css
description: "Styles interfaces using Tailwind CSS utility classes, custom config, responsive design, and component extraction patterns."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: Tailwind, Tailwind CSS, utility class, responsive, dark mode, @apply, CSS, style, layout, flex, grid, design system
  role: specialist
  scope: implementation
  output-format: code
  related-skills: frontend-ui-engineering, designing-frontend-interfaces, css-in-js, shadcn-ui
---

# Tailwind CSS

Style UIs with utility-first CSS: responsive breakpoints, dark mode, custom themes, `@apply`, plugins, and component extraction patterns.

## When to Use This Skill

- Building consistent designs rapidly with utility-first CSS classes
- Implementing responsive layouts across mobile, tablet, and desktop breakpoints
- Configuring custom design systems with brand colors, fonts, and spacing scales
- Styling components in framework-agnostic projects (React, Vue, Svelte, Astro)
- Creating dark mode support with Tailwind's `dark:` variant and class-based toggling

## Key Capabilities

- **Utility-First Workflow** — Compose complex designs from single-purpose utility classes directly in markup, eliminating context-switching between HTML and CSS files
- **Responsive Design** — Apply breakpoint-aware styles with `sm:`, `md:`, `lg:`, `xl:`, and `2xl:` prefixes, plus arbitrary breakpoints with `min-[…]:` and `max-[…]:`
- **Custom Configuration** — Extend the default theme in `tailwind.config.*` with custom colors, fonts, spacing, breakpoints, and animations while retaining framework defaults
- **Dark Mode** — Implement dark mode with the `dark:` variant using class-based (`class` strategy) or system-preference (`media` strategy) toggling
- **Component Extraction** — Extract repeated utility patterns into reusable component classes using `@apply`, or create custom utility groups with plugins
- **Design System Tokens** — Define and enforce design tokens (colors, spacing, typography) through the config, providing a single source of truth across teams

## Best Practices

- Stay close to the defaults: override as little as possible in `tailwind.config.*` to keep the generated CSS small and the design system coherent
- Use `@apply` sparingly and only for highly repeated patterns within a component; overusing it defeats the utility-first advantage and creates specificity problems
- Prefer Tailwind's built-in state variants (`hover:`, `focus:`, `active:`, `disabled:`) over writing custom CSS for pseudo-classes
- Leverage arbitrary values (`top-[37px]`, `grid-cols-[200px_1fr]`) when the design token scale doesn't fit, rather than bloating the config
- Install the Tailwind CSS IntelliSense extension for class autocompletion, linting, and hover previews to improve workflow speed
