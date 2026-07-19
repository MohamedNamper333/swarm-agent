---
name: storybook
description: Develops and documents UI components in isolation using Storybook with CSF, addons, and test integration.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: frontend
  triggers: Storybook, story, CSF, Component Story Format, addons, controls, a11y, visual testing, interaction testing
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, playwright-expert, shadcn-ui, tailwind-css
---

# Storybook

Storybook is a frontend workshop for building UI components in isolation. It supports Component Story Format (CSF), a rich addon ecosystem (controls, accessibility, actions, viewport, docs), interaction testing with Jest and Testing Library, and visual regression testing via Chromatic or Playwright.

## When to Use This Skill

- Developing and documenting a component library with Storybook's auto-generated Docs pages and controls
- Writing stories in CSF 3 format for React, Vue, Angular, Svelte, or Web Components
- Adding interaction tests that simulate clicks, form input, and async behavior inside stories
- Setting up visual regression testing with Chromatic or Storybook test runner for UI change detection
- Configuring addons — controls (props table), a11y (axe-core), actions (event logger), viewport (responsive preview)

## Key Capabilities

- CSF 3 stories — Write stories as concise `export const` objects with args, play functions, and loading states
- Args and controls — Define component props as args; let users manipulate them live via auto-generated controls (text, boolean, select, color)
- Interaction testing — Import `within` and `userEvent` from `@storybook/test` to write play functions that verify UI behavior
- Addon ecosystem — Install addons for accessibility audits, design measurements, story organization, themes, and mock service workers
- Visual testing integration — Export Storybook to Chromatic for UI review with pixel-level diffs, or use the test-runner with Playwright for screenshot comparison

## Best Practices

- Co-locate `.stories.tsx` files next to components rather than in a global `stories/` folder to keep them maintainable
- Use the `meta` default export to set a shared `decorators`, `parameters`, and `argTypes` for all stories in a file
- Avoid network calls inside stories — mock API data with `parameters` or MSW addon so stories render reliably in isolation
