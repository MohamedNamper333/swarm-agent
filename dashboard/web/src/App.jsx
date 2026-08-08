import { useState, useEffect } from 'react'
import VaultSearch from './components/VaultSearch.jsx'
import AgentCards from './components/AgentCards.jsx'
import PipelineMonitor from './components/PipelineMonitor.jsx'
import api from './api/client.js'

export default function App() {
  const [health, setHealth] = useState({ status: 'checking' })
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    check()
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const check = async () => {
    const h = await api.health()
    setHealth(h)
  }

  const time = now.toLocaleTimeString('en-US', { hour12: false })
  const date = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1 className="app-title">
            <span className="logo" aria-hidden="true">🐝</span>
            Swarm Agent Dashboard
        </h1>
          <p className="app-subtitle">
            Phase 3 · Week 14 · Resilience · Observability · API · Plugins
        </p>
      </div>
        <div className="app-meta">
          <span className="mono muted" aria-label="current time">
            {date} {time}
        </span>
          <button
            className={`badge ${health.status === 'healthy' ? '' : health.status === 'offline' ? 'err' : 'warn'}`}
            onClick={check}
            aria-label="Backend health status — click to refresh"
          >
            <span className="badge-dot" />
            {health.status || 'unknown'}
        </button>
      </div>
    </header>

      <PipelineMonitor />
      <AgentCards />
      <VaultSearch />
  </div>
  )
}
