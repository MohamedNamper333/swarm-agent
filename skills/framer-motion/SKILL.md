---
name: framer-motion
description: Use when building animations, transitions, gestures, and layout animations with Framer Motion in React applications. Invoke for motion components, variants, AnimatePresence, gesture handlers, scroll animations, SVG animations, and shared layout animations.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: frontend
  triggers: Framer Motion, animation, motion, AnimatePresence, variants, gesture, drag, layout animation, scroll animation, whileHover, whileTap, spring, keyframes, SVG animation, motion component, useAnimation, useMotion
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, designing-frontend-interfaces, frontend-ui-engineering, tailwind-css
---

# Framer Motion

Framer Motion is a production-grade animation library for React that provides declarative animations through the `motion` component API, layout animations with automatic diffing, gesture recognition (drag, hover, tap, pan), and rich orchestration via variants and `AnimatePresence`.

## When to Use This Skill

- Adding enter/exit animations to React components with `AnimatePresence` and `motion.div`
- Implementing gesture-driven interactions — drag, swipe, hover, and tap with spring physics
- Building shared layout animations and smooth page transitions between routes
- Orchestrating complex multi-child animations with variants, stagger, and sequence control

## Key Capabilities

- Create declarative animations with the `motion` component API using `initial`, `animate`, `exit`, and `transition` props
- Orchestrate coordinated animations across multiple children using variants with `staggerChildren` and `delayChildren`
- Implement drag, swipe, and gesture-based interactions with momentum, bounds, and snap targets
- Use `AnimatePresence` and `layout` animations for smooth enter/exit and layout-shift transitions

## Best Practices

- Use `layoutId` for shared layout animations between different components that represent the same element
- Prefer variants over individual component animation props when coordinating multi-child sequences
- Set `transition={{ type: 'spring', stiffness: 300, damping: 30 }}` for natural-feeling UI motion
- Always provide `key` to children of `AnimatePresence` so it accurately tracks element lifecycle

## Core Workflow

1. **Import** — Import `motion` from `framer-motion` and `AnimatePresence` for enter/exit animations
2. **Animate** — Use `initial` and `animate` props for basic enter animations on mount
3. **Orchestrate** — Define variants object and pass variant names to animate coordinated children
4. **Interact** — Add `whileHover`, `whileTap`, `whileDrag`, `drag`, and `whileInView` for interactive motion
5. **Transition** — Wrap route or conditional content with `AnimatePresence` for exit animations

## Key Patterns

```tsx
// Enter/Exit animation with AnimatePresence
import { motion, AnimatePresence } from 'framer-motion';

export function Notification({ message, onClose }: Props) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          key="notification"
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          layout
          style={{ padding: 16, background: '#333', color: '#fff', borderRadius: 8 }}
        >
          {message}
          <button onClick={onClose}>✕</button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

```tsx
// Variants with stagger children
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { type: 'spring', stiffness: 300 },
  },
};

export function List({ items }: { items: string[] }) {
  return (
    <motion.ul variants={containerVariants} initial="hidden" animate="visible">
      {items.map((item) => (
        <motion.li key={item} variants={itemVariants}>
          {item}
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

## Constraints

### MUST DO
- Use `layout` prop on elements whose position changes due to other elements animating
- Add `key` prop to all children inside `AnimatePresence` for proper lifecycle tracking
- Use `whileInView` for scroll-triggered animations instead of manual intersection observers

### MUST NOT DO
- Animate `height: auto` directly — use `layout` prop instead for automatic height transitions
- Use framer-motion for simple CSS transitions (prefer CSS for opacity, color, and 2D transforms)
- Omit `exit` prop when using `AnimatePresence` — every animated child needs an exit defined
