---
name: tauri
description: "Builds lightweight cross-platform desktop applications using Tauri with Rust backend and web frontend."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: desktop
  triggers: Tauri, Rust, desktop app, system tray, tauri::command, invoke, shell, file system, bundling, cross-platform
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, tailwind-css, frontend-ui-engineering, rust-engineer, electron
---

# Tauri

Lightweight desktop apps: Rust backend commands, web frontend (any framework), system tray, file system access, and bundling.

## When to Use This Skill

- Building cross-platform desktop applications with a small binary footprint (under 10MB)
- Creating secure desktop apps where the Rust backend enforces permission-based capability access
- Combining a web-based UI (React, Vue, Svelte, Solid) with a high-performance Rust backend
- Building system-level tools (file manager, media player, dev tool) that need native OS access
- Replacing an Electron app with a lighter, faster, more secure alternative

## Key Capabilities

- **Rust Backend Commands** — Expose Rust functions to the frontend via `#[tauri::command]` and `invoke()` for high-performance, type-safe backend logic
- **Web Frontend (Any Framework)** — Bring your own UI stack: React, Vue, Svelte, Solid, or vanilla HTML/CSS/JS — Tauri renders with the OS webview (WebKit on macOS/Linux, WebView2 on Windows)
- **Capability-Based Security** — Configure granular permissions in `tauri.conf.json` and Capabilities files: control which commands, files, shells, and HTTP requests each window can access
- **Plugin Ecosystem** — Extend Tauri with official plugins for file dialogs, shell commands, SQLite, file system access, HTTP requests, notifications, clipboard, and more
- **System Tray & Native Menus** — Implement system tray icons with context menus, native application menus, and dock/taskbar integration via the Tauri API
- **Cross-Platform Bundling** — Build platform-specific installers (`.dmg`, `.msi`, `.deb`, `.AppImage`) with Tauri's bundler, including code signing and auto-update support

## Best Practices

- Design with capability-based security: grant each window only the minimum permissions needed, never use the blanket `"core:default"` for production apps
- Structure Rust commands with clear error types using `Result<T, E>` and return meaningful error messages that the frontend can display
- Keep the webview layer pure UI logic — perform expensive computation, file I/O, and system calls in Rust commands rather than JavaScript
- Use Tauri's `tauri::path` API for portable file paths instead of hardcoding OS-specific directory locations
- Configure `tauri.conf.json` identifier and build settings early; changing the identifier after distribution breaks auto-update and keychain access
