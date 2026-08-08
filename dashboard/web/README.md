# Swarm Agent Dashboard

React dashboard for monitoring the Swarm Agent system. Part of Phase 3 Week 14.

## Components

- **PipelineMonitor** — Live task pipeline (pending/running/completed/failed) with sparkline chart
- **AgentCards** — Active agents with health indicator and task counter
- **VaultSearch** — Knowledge vault full-text search

## Setup

```bash
cd dashboard/web
npm install
npm run dev
```

Dashboard starts on `http://localhost:5173` and proxies API calls to `http://localhost:8080`.

## Configuration

Set `VITE_API_BASE` env var to override the proxy target:

```bash
VITE_API_BASE=http://your-server:8080 npm run dev
```

## Build

```bash
npm run build    # outputs to dist/
npm run preview  # serve dist/
```

## Architecture

```
dashboard/web/
├── package.json
├── vite.config.js
├── public/index.html
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── styles.css
    ├── api/client.js          # REST + WebSocket client
    └── components/
        ├── PipelineMonitor.jsx
        ├── AgentCards.jsx
        └── VaultSearch.jsx
```

Polling interval: 2-3s per panel. Falls back to empty state if API is offline.
