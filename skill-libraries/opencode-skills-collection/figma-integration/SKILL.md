---
name: figma-integration
description: Integrates Figma design data into code workflows using the Figma API, plugins, and design tokens export.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: design-tools
  triggers: Figma, Figma API, design tokens, plugin, design-to-code, components, variables, webhook, file
  role: specialist
  scope: implementation
  output-format: code
  related-skills: shadcn-ui, tailwind-css, react-expert, frontend-ui-engineering
---

# Figma Integration

Figma is a collaborative design tool whose REST API enables reading file data, extracting component metadata, accessing local variables (design tokens), and syncing designs to code. This skill covers the Figma REST API, plugin development with the iframe-based plugin API, design token export workflows, and webhook-based sync.

## When to Use This Skill

- Extracting design tokens (colors, typography, spacing, shadows) from Figma variables and syncing them to CSS, Tailwind, or Style Dictionary
- Reading Figma file nodes — pages, frames, components, and their properties — via the REST API for documentation or code generation
- Building a Figma plugin that transforms selected layers into React components, SVG exports, or JSON configurations
- Setting up webhook subscriptions to notify your codebase of design changes (file update, version publish, comment)
- Synchronizing Figma component metadata with a Storybook or design system documentation page

## Key Capabilities

- Figma REST API — Fetch file data, images, component sets, styles, and comments using `GET /v1/files/:key` and `GET /v1/images/:key`
- Design token extraction — Read local variables (`/v1/files/:key/variables/local`) and collections to generate CSS custom properties, Tailwind configs, or Style Dictionary JSON
- Plugin development — Write Figma plugins (TypeScript/HTML) with the plugin API — access `figma.currentPage`, create nodes, export SVGs, and show custom UIs
- Webhook integration — Subscribe to `FILE_UPDATE`, `FILE_VERSION_UPDATE`, and `FILE_COMMENT` events to keep your codebase in sync with design changes
- Component sync — Map Figma component hierarchies to React/Vue component props by reading `componentPropertyDefinitions` from the REST API

## Best Practices

- Store the Figma `personalAccessToken` in environment variables and never commit it to version control; scope tokens to the minimum required file access
- Use Figma variable collections (not raw styles) for design tokens since variables support modes (light/dark) and aliasing natively
- Cache API results aggressively — Figma REST API has rate limits (200 requests per minute per token) and file responses can be large for big design files
