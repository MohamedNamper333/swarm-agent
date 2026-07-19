---
name: vite
description: Use when configuring Vite for frontend builds, optimizing development workflow, setting up plugins, customizing HMR, and tuning production builds. Invoke for Vite configuration, SSR setup, environment variables, CSS preprocessing, code splitting, lazy loading, and build performance optimization.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: frontend
  triggers: Vite, vite.config, HMR, Rollup, ESBuild, build tool, bundler, frontend tooling, Vite dev server, code splitting, lazy loading, CSS modules, PostCSS, SSR
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, vue-expert, nextjs-developer, svelte, tailwind-css
---

# Vite

Vite is a next-generation frontend build tool that leverages native ES modules for an instant dev server startup and lightning-fast HMR. It uses Rollup for production bundling with tree-shaking, code splitting, and fine-grained caching. Vite supports React, Vue, Svelte, Solid, and vanilla JS out of the box.

## When to Use This Skill

- Scaffolding a new project with `create-vite` or migrating an existing project to Vite
- Configuring plugins, resolve aliases, CSS preprocessing, and environment variables
- Optimizing production builds with manual chunks, asset inlining, and minification
- Setting up SSR or library mode for custom build targets

## Key Capabilities

- Configure Vite plugins (official, community, or custom) for framework integration, linting, and optimization
- Tune build output with Rollup options — manual chunks, `build.rollupOptions.output`, and `build.target`
- Manage environment variables with `import.meta.env` and custom `.env` mode files
- Implement CSS solutions — PostCSS, CSS Modules, preprocessors (Sass, Less), and Lightning CSS

## Best Practices

- Use `vite-plugin-checker` for type-checking and linting in a separate thread to avoid blocking the dev server
- Configure `build.rollupOptions.output.manualChunks` to separate vendor code from application code
- Leverage Vite's built-in CSS handling rather than adding webpack-style loaders — Vite natively supports PostCSS, CSS Modules, and preprocessors
- Set environment prefixes with `envPrefix` to expose only intended variables to client code

## Core Workflow

1. **Scaffold** — Run `npm create vite@latest` with your framework template
2. **Configure** — Edit `vite.config.ts` with plugins, aliases, proxy, and build settings
3. **Develop** — Use `vite dev` for instant HMR-powered development
4. **Build** — Run `vite build` for optimized production output
5. **Preview** — Use `vite preview` to test the production build locally

## Key Patterns

```typescript
// vite.config.ts — Complete setup with React, aliases, and chunk splitting
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';

export default defineConfig({
  plugins: [
    react(),
    tsconfigPaths(),
    checker({ typescript: true }),
  ],
  resolve: {
    alias: { '@': '/src' },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
  server: {
    proxy: { '/api': 'http://localhost:3000' },
  },
});
```

## Constraints

### MUST DO
- Use `vite.config.ts` (not `.js`) for full TypeScript support in configuration
- Configure the dev server proxy for local API development to avoid CORS issues
- Set `build.sourcemap` based on your error-tracking needs (usually `hidden` for production)

### MUST NOT DO
- Use CommonJS syntax in `vite.config.ts` — Vite treats config files as ESM by default
- Commit `.env` files with secrets — use `.env.example` for documentation
- Bundle large dependencies without manual chunk configuration (bloats initial load)
