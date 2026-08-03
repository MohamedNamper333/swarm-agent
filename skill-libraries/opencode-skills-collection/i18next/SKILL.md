---
name: i18next
description: "Implements internationalization using i18next with translation files, language detection, and React/Next.js integration."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: frontend
  triggers: i18n, i18next, internationalization, localization, translation, L10n, language, multilingual, react-i18next, next-i18next
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, nextjs-developer, vue-expert, angular-architect, svelte
---

# i18next / Internationalization

Internationalization (i18n) specialist — configures i18next with translation files, language detection, namespacing, interpolation, pluralization, date/number formatting, and framework bindings (react-i18next, next-i18next, vue-i18next, ngx-translate).

## When to Use This Skill

- Adding multi-language support to a web app with translation files (JSON, YAML, or remote bundles)
- Setting up automatic language detection from URL path, cookie, localStorage, or browser `Accept-Language` header
- Formatting dates, times, numbers, and currencies per locale using i18next's `Intl` integration
- Handling pluralization rules and gender-aware translations for languages with complex grammar (Arabic, Russian, Polish)
- Integrating i18next with React, Next.js, Vue, Angular, or Svelte via dedicated bindings

## Key Capabilities

- Configure i18next instance with detection, backend loading, caching, and fallback language chains
- Organize translations using namespaces (e.g., `common`, `errors`, `checkout`) for modular loading and lazy-loading
- Use interpolation (`{{variable}}`), nesting (`$t(key)`), plurals (`key_one`, `key_other`), context (`key_male`, `key_female`), and formatting via `format` function
- Integrate react-i18next: `useTranslation()` hook, `Trans` component with embedded HTML, and `appWithTranslation` for Next.js SSR
- Extract and pseudo-localize strings for translation handoff — generate missing key reports, sort translation files, and validate coverage

## Best Practices

- Always nest translations by feature or page namespace rather than one flat file — keeps bundles small and loading lazy
- Use `Trans` component instead of dangerously setting innerHTML when translations contain inline markup or links
- Set a strict `saveMissing` / `parseMissingKeyHandler` in development so missing translations surface immediately instead of silently falling back
