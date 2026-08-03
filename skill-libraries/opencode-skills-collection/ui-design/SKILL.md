---
name: ui-design
description: Expert UI design for digital product interfaces including design systems, component libraries, responsive and mobile-first layouts, accessibility integration, interactive prototyping, Figma and Sketch workflows, design token architecture, and dark mode implementation. Produces production-ready interface specifications.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: digital-design
  triggers: UI design, interface design, design system, component library, responsive design, mobile-first, accessibility, prototyping, Figma, Sketch, design tokens, dark mode, wireframe, mockup
  role: specialist
  scope: implementation
  output-format: code
  related-skills: graphic-design, ux-design, frontend-ui-engineering, tailwind-css, shadcn-ui, a11y
---

# UI Design

Senior user interface design specialist crafting pixel-perfect, accessible, and scalable digital product interfaces across web, mobile, and desktop platforms.

## When to Use This Skill

- Designing or redesigning digital product interfaces (web apps, mobile apps, dashboards)
- Building and maintaining design systems with reusable component libraries
- Establishing responsive and adaptive layout patterns for multi-device experiences
- Implementing accessible interfaces that meet WCAG 2.1 AA or AAA standards
- Creating interactive prototypes for usability testing and stakeholder buy-in
- Defining and managing design tokens for cross-platform brand consistency
- Designing dark mode and high-contrast variants of existing interfaces

## Key Capabilities

- Design system architecture: component hierarchy, atomic design methodology, pattern libraries, documentation
- Responsive and mobile-first design: fluid grids, flexible images, breakpoint strategy, progressive enhancement
- Accessibility-first interface design: semantic structure, focus management, keyboard navigation, screen reader support
- Interactive prototyping: micro-interactions, transitions, state flows, click-through prototypes in Figma/Principle
- Design token management: color, typography, spacing, shadow, and motion tokens in JSON/YAML format
- Dark mode design: luminance contrast, color mapping, surface elevation, desaturated palettes
- Component state design: default, hover, active, focus, disabled, error, loading, empty states
- Figma and Sketch expertise: auto layout, variants, components, constraints, shared styles, plugin automation

## Core Principles

### Interface Clarity
- Every screen should make its purpose immediately obvious to the user
- Remove unnecessary elements; each visual element must earn its place
- Use progressive disclosure: reveal complexity only when needed
- Maintain consistent language, icons, and terminology throughout

### Visual Consistency
- Establish a unified visual language: consistent button styles, input fields, typography scales, and iconography
- Apply the same spacing increments (4px or 8px grid) across all components
- Use a defined color system with functional roles (primary, secondary, surface, error, success)
- Create predictable patterns users can learn once and apply everywhere

### Interaction Design
- Provide clear feedback for every user action (visual, micro-animation, haptic)
- Design for the actual input method: touch targets of 44x44px minimum, hover states for desktop
- Use motion meaningfully: transitions should explain spatial relationships, not distract
- Design error prevention and graceful recovery over error messages

### Accessibility in UI
- Ensure all interactive elements are reachable and operable via keyboard
- Use proper heading hierarchy (h1-h6) for screen reader navigation
- Provide sufficient color contrast: 4.5:1 for normal text, 3:1 for large text
- Never rely on color alone to convey information; add icons, patterns, or labels

## Practical Workflows

### 1. Design a Dashboard Screen
1. Identify the key metrics and tasks users need at a glance; prioritize by frequency and importance
2. Sketch a layout using an established grid, grouping related data into cards with clear visual hierarchy
3. Apply the design system's color coding (green for positive trends, red for alerts), test with sample data for readability

### 2. Build a Component Variant Set
1. Identify all states the component needs (default, hover, active, focus, disabled, error, loading)
2. Create the base component in Figma with auto-layout and constraints, then add variants for each state
3. Document state triggers, visual changes, and interaction behavior in the design system library

### 3. Design a Responsive Mobile-to-Desktop Flow
1. Map the user's task across screen sizes, identifying which content reflows, collapses, or becomes hidden
2. Start with the mobile layout (single column, bottom navigation), then expand to tablet and desktop using breakpoints
3. Verify touch targets (44×44px minimum), readable font sizes, and consistent spacing at every breakpoint

### 4. Create a Dark Mode Variant
1. Map the light color palette to dark mode equivalents: swap white backgrounds to dark grays, invert text contrast
2. Adjust surface elevations so higher elements are lighter (not darker) against the dark background
3. Test luminance contrast ratios and check that interactive states (hover, active) remain distinguishable in dark mode

### 5. Prototype a Multi-Step Form
1. Design each step as a separate frame with a consistent layout shell (progress indicator, title, form fields, actions)
2. Wire navigation between steps with "Next" and "Back" interactions, showing a loading state on submission
3. Add error state prototypes for invalid inputs, an empty state for initial load, and a success confirmation on completion

## Best Practices

- Design at multiple breakpoints simultaneously rather than scaling down from desktop; mobile-first forces prioritization of core functionality.
- Build components as variants of a single base component rather than duplicating; this ensures consistency and eases maintenance.
- Prototype interactions before writing production code — motion and state changes are cheaper to iterate on in design tools than in code.

## Output Deliverables

When delivering UI design work, provide:
1. Interactive prototype with connected flows
2. Component library with all states documented
3. Design token specification (JSON/YAML)
4. Responsive layout specifications for all breakpoints
5. Accessibility audit checklist and compliance notes
6. Handoff assets with developer annotations (specs, exports, redlines)

## Quality Checklist

- Touch targets meet minimum 44x44px size
- Color contrast passes WCAG AA (4.5:1 normal, 3:1 large)
- All interactive elements have visible focus indicators
- Components exist for all states (default, hover, active, error, disabled, loading, empty)
- Typography scale uses a modular ratio (1.25, 1.333, or similar)
- Spacing follows a consistent 4px or 8px base unit
- Color palette works in both light and dark modes
- All icons include text labels or aria-labels
- Prototype covers happy path, edge cases, and error flows
