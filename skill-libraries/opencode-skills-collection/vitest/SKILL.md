---
name: vitest
description: Use when writing unit tests, integration tests, or component tests with Vitest in Vite-based projects. Invoke for test configuration, mocking strategies, code coverage, snapshot testing, and browser-based testing with Playwright or Happy DOM.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: testing
  triggers: Vitest, unit test, integration test, coverage, mocking, vi.mock, vi.fn, snapshot, test runner, JSDOM, Happy DOM, test configuration, in-source testing, benchmark
  role: specialist
  scope: implementation
  output-format: code
  related-skills: vite, react-expert, vue-expert, playwright-expert, test-master, test-driven-development
---

# Vitest

Vitest is a blazing-fast unit test framework powered by Vite, providing Jest-compatible API with native ESM support, HMR for tests, and Vite's plugin ecosystem. It supports component testing with Happy DOM or JSDOM, built-in coverage via c8/istanbul, and parallel execution out of the box.

## When to Use This Skill

- Writing unit and integration tests for Vite-based projects (React, Vue, Svelte, vanilla)
- Configuring Vitest with custom setup files, globals, environment, and coverage thresholds
- Mocking modules, timers, and functions with `vi.mock`, `vi.fn`, and `vi.spyOn`
- Running component tests with DOM emulation or browser-mode testing

## Key Capabilities

- Configure test environments per file using `// @vitest-environment happy-dom` pragma comments
- Mock ES modules, Node built-ins, and global objects with Vitest's `vi` utility
- Generate coverage reports with `@vitest/coverage-v8` or `@vitest/coverage-istanbul`
- Run tests in parallel with watch mode and automatic re-run on file changes

## Best Practices

- Use `vi.mock` at the top level for module mocking and `vi.fn` for inline function stubs
- Set `globals: true` in vitest.config only if your codebase consistently uses global test functions (describe, it, expect)
- Configure `setupFiles` for global mocks, polyfills, or cleanup between test runs
- Always clean up mocks between tests using `vi.clearAllMocks()` in `afterEach` or `beforeEach`

## Core Workflow

1. **Configure** — Create `vitest.config.ts` extending your Vite config with test-specific settings
2. **Write** — Place tests co-located with source files as `*.test.ts` or in a `__tests__/` directory
3. **Run** — Execute `vitest` for watch mode or `vitest run` for single-pass CI runs
4. **Cover** — Add `--coverage` to measure line, branch, and function coverage

## Key Patterns

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: { lines: 80, functions: 80, branches: 75, statements: 80 },
    },
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
```

```typescript
// Component test with mocking
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserProfile } from './UserProfile';

vi.mock('./api', () => ({
  fetchUser: vi.fn().mockResolvedValue({ id: '1', name: 'Alice' }),
}));

describe('UserProfile', () => {
  it('renders user name after loading', async () => {
    render(<UserProfile userId="1" />);
    expect(await screen.findByText('Alice')).toBeDefined();
  });
});
```

## Constraints

### MUST DO
- Configure `environment` explicitly — JSDOM or Happy DOM based on your DOM API needs
- Use `vi.useFakeTimers` and `vi.useRealTimers` in pairs when testing time-dependent code
- Set coverage thresholds in CI to enforce minimum coverage levels

### MUST NOT DO
- Share mutable state across test files (each test file should be isolated)
- Mock modules you don't own without understanding their internal API surface
- Use `vi.mock` inside test functions — hoist it to the top level
