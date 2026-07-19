---
name: a11y
description: "Implements web accessibility (WCAG) standards: ARIA, keyboard navigation, screen reader support, and color contrast."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: frontend
  triggers: accessibility, a11y, WCAG, ARIA, screen reader, keyboard navigation, color contrast, focus management, 508, ADA, inclusive design
  role: specialist
  scope: implementation
  output-format: code
  related-skills: frontend-ui-engineering, react-expert, vue-expert, angular-architect, svelte, tailwind-css
---

# Accessibility (a11y)

Web accessibility specialist — implements WCAG 2.2 AA/AAA compliance, semantic HTML, ARIA patterns, keyboard navigation, screen reader compatibility, focus management, and color contrast throughout the UI.

## When to Use This Skill

- Auditing and remediating existing UI for WCAG 2.2 AA compliance
- Building accessible form controls, modals, dialogs, tooltips, dropdowns, and other interactive widgets
- Implementing keyboard navigation patterns (Tab, arrow keys, Escape, role-based shortcuts)
- Adding ARIA landmarks, live regions, and accessible names to complex components
- Ensuring sufficient color contrast ratios and supporting forced-colors / high-contrast mode

## Key Capabilities

- Apply semantic HTML structure — landmarks (`<nav>`, `<main>`, `<aside>`), heading hierarchy (`h1`-`h6`), and proper form labeling (`<label>`, `aria-labelledby`, `aria-describedby`)
- Implement ARIA design patterns from WAI-ARIA Authoring Practices — combobox, dialog, tabs, accordion, carousel, treeview, and grid
- Manage focus: programmatic focus management (`focus()`), focus trapping in modals, `inert` attribute, and `:focus-visible` styling
- Ensure screen reader feedback with `aria-live` regions, `aria-atomic`, `role="alert"`, and `aria-relevant` for dynamic content updates
- Validate color contrast (WCAG AA: 4.5:1 normal, 3:1 large text; AAA: 7:1 normal, 4.5:1 large) and support prefers-reduced-motion, prefers-color-scheme, and forced-colors media queries

## Best Practices

- Prefer native HTML semantics over ARIA — use `<button>` instead of `<div role="button">` whenever possible
- Test with real assistive technology (VoiceOver, NVDA, JAWS) and automated tools (axe-core, Lighthouse, WAVE) — never rely on automation alone
- Ensure all functionality is available via keyboard alone — no mouse-dependent interactions without keyboard equivalents
