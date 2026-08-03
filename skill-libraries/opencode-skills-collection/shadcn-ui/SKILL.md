---
name: shadcn-ui
description: Builds UI components using shadcn/ui with Tailwind CSS, Radix primitives, and customizable themes.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: frontend
  triggers: shadcn, shadcn/ui, Radix, Tailwind, components, Button, Card, Dialog, theme, design system
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, react-expert, storybook, figma-integration
---

# shadcn/ui

shadcn/ui is a collection of re-usable React components built on Radix UI primitives and styled with Tailwind CSS. Unlike traditional component libraries, shadcn/ui components are copied into your project as source code so you can customize them directly.

## When to Use This Skill

- Adding accessible and customizable UI components (Button, Dialog, Dropdown, Sheet, Table, Tabs, etc.) to a React project
- Initializing shadcn/ui in a Next.js, Vite, or Remix project with `npx shadcn@latest init`
- Customizing the base theme (colors, borders, fonts, radius) via the `cn` utility and CSS variables
- Combining shadcn/ui components to build complex patterns — forms, data tables, side panels, and navigation layouts
- Extending or composing existing shadcn/ui source files to add domain-specific behavior

## Key Capabilities

- Component initialization — Run `npx shadcn@latest add button` to copy individual components into `@/components/ui/` with full source control
- Radix primitives — Accessible, headless foundation for Dialog, Popover, DropdownMenu, Select, Tabs, Toast, and more
- Theme customization — Modify `globals.css` CSS variables (`--primary`, `--secondary`, `--radius`) and update `tailwind.config.ts` for a custom design system
- Composition — Combine primitives (e.g., Dialog + Form + Select) to build production-grade modals, multi-step wizards, and filter panels
- Dark mode — Toggle between light and dark palettes with a `class` strategy and the `next-themes` or `next/dark-mode` integration

## Best Practices

- Never edit the component source files directly inside `node_modules` — always add the component to your project and edit the local copy
- Keep the global CSS variables (`globals.css`) as the single source of truth for colors and spacing to maintain visual consistency
- Add components on-demand rather than bulk-adding all available components to avoid dead code and reduce bundle size
