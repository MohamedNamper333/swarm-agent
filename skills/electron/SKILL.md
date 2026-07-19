---
name: electron
description: "Builds cross-platform desktop applications using Electron with IPC, native APIs, and auto-update workflows."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: desktop
  triggers: Electron, electron-builder, main process, renderer process, preload, IPC, ipcMain, ipcRenderer, contextBridge, native API, auto-update, BrowserWindow
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, tailwind-css, tauri, frontend-ui-engineering
---

# Electron

Desktop apps: main/renderer process, IPC communication, native dialogs, auto-update, packaging with electron-builder, and security best practices.

## When to Use This Skill

- Building cross-platform desktop applications with web technologies (HTML/CSS/JS)
- Implementing native OS integrations (file system, dialogs, notifications, tray)
- Architecting secure IPC communication between main and renderer processes
- Setting up auto-update pipelines for distribution to end users
- Packaging and distributing applications with electron-builder or Electron Forge

## Key Capabilities

- **Process Architecture** — Master Electron's two-process model: main process (Node.js, system access) and renderer process (Chromium, UI), connected via preload scripts with `contextBridge`
- **IPC Communication** — Establish secure main↔renderer communication with `ipcMain.handle` / `ipcRenderer.invoke` (request-response) and `webContents.send` / `ipcRenderer.on` (push messages)
- **Native APIs** — Access OS-level features: native file dialogs (`dialog.showOpenDialog`), system tray (`Tray`), notifications (`Notification`), menu bar (`Menu`), and clipboard
- **Auto-Update** — Implement seamless app updates with `electron-updater` (electron-builder) or `autoUpdater` (Squirrel), including delta updates and staged rollouts
- **Security Hardening** — Apply security best practices: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, Content Security Policy headers, and preload-only exposure
- **Packaging & Distribution** — Package apps with electron-builder (`.dmg`, `.exe`, `.AppImage`, `.snap`), code signing, notarization for macOS, and Windows installer configuration

## Best Practices

- Always enable `contextIsolation: true` and `nodeIntegration: false` in production to prevent remote code execution via renderer compromise
- Expose specific APIs through `contextBridge` in the preload script rather than exposing `ipcRenderer` directly to the renderer
- Use `ipcMain.handle` / `ipcRenderer.invoke` (async message passing) over the old `send`/`on` pattern to get proper request-response semantics
- Keep the main process lean — move heavy computation to child processes or worker threads to avoid blocking the UI
- Configure auto-update early in development: test update flows on CI before shipping to avoid broken distribution pipelines at launch
