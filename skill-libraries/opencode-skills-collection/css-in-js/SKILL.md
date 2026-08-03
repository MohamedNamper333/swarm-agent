---
name: css-in-js
description: "Implements styling using CSS-in-JS solutions like styled-components, Emotion, Stitches, and vanilla-extract."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: styled-components, Emotion, Stitches, vanilla-extract, CSS-in-JS, styled, css prop, theming, SSR, design tokens
  role: specialist
  scope: implementation
  output-format: code
  related-skills: tailwind-css, frontend-ui-engineering, designing-frontend-interfaces, react-expert
---

# CSS-in-JS

Style components with CSS-in-JS libraries: styled-components, Emotion, Stitches, vanilla-extract — dynamic styles, theming, SSR compatibility.

## When to Use This Skill

- Building component-scoped styles with dynamic props-based styling
- Implementing design system theming with runtime or build-time tokens
- Creating reusable styled primitives across a React/Preact component library
- Working with SSR frameworks that need extracted CSS at build time
- Migrating between CSS-in-JS libraries or adopting zero-runtime solutions

## Key Capabilities

- **Styled Components** — Create styled React components with tagged template literals, automatic vendor prefixing, and props interpolation
- **Emotion CSS Prop** — Apply ad-hoc styles with the `css` prop for inline dynamic styling without creating wrapper components
- **Stitches Variants** — Design component APIs with typed variants, compound variants, and responsive prop-based styling using Stitches' atomic CSS approach
- **vanilla-extract Zero-Runtime** — Write TypeScript/CSS files that generate static CSS at build time with full type safety and no runtime overhead
- **Theming Systems** — Provide and consume themes through `ThemeProvider` (styled-components/Emotion) or config-level tokens (Stitches/vanilla-extract)
- **SSR Extraction** — Configure server-side rendering with critical CSS extraction (styled-components' `StyleSheetManager`, Emotion's `extractCritical`, vanilla-extract's static output)

## Best Practices

- Prefer vanilla-extract or Linaria for production apps where bundle size matters — runtime CSS-in-JS adds 10–15KB to the bundle
- Keep styled components in co-located `*.styles.ts` files rather than mixing them into component logic files for separation of concerns
- Define theme tokens in a dedicated theme file and import them consistently rather than hardcoding color/spacing values in individual components
- Use component variants (Stitches' `variant`, styled-components' props interpolation) instead of conditional class name concatenation for cleaner APIs
- Avoid over-nesting in styled-components templates; prefer flat, single-level styles to match the component's flat DOM structure
