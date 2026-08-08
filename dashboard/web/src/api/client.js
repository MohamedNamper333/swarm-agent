import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE || ''

// REST server exposes routes WITHOUT an /api prefix; vite proxies /api/* to backend.
// We strip the /api prefix so requests hit the real FastAPI routes.
const strip = (path) => path.replace(/^\/api/, '')

export const api = {
  health: () => axios.get(`${BASE}/api/health`).then(r => r.data).catch(() => ({ status: 'offline' })),
  agents: () => axios.get(`${BASE}/api/agents`).then(r => r.data).catch(() => []),
  tasks: () => axios.get(`${BASE}/api/tasks`).then(r => r.data).catch(() => []),
  metrics: () => axios.get(`${BASE}/api/metrics`).then(r => r.data).catch(() => null),
  vault: (q) => axios.get(`${BASE}/api/vault/search?q=${encodeURIComponent(q)}`).then(r => r.data).catch(() => []),
  snapshots: () => axios.get(`${BASE}/api/snapshots`).then(r => r.data).catch(() => []),
}

export default api
