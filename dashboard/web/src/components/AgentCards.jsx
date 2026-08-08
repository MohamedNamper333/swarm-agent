import { useEffect, useState } from 'react'
import api from '../api/client.js'

const STATE_CLASS = {
  idle: 'idle',
  running: 'busy',
  busy: 'busy',
  error: 'error',
  failed: 'error',
  stopped: 'idle',
}

function fmtAgo(iso) {
  if (!iso) return '—'
  const d = (Date.now() - new Date(iso).getTime()) / 1000
  if (d < 60) return Math.round(d) + 's ago'
  if (d < 3600) return Math.round(d / 60) + 'm ago'
  return Math.round(d / 3600) + 'h ago'
}

export default function AgentCards() {
  const [agents, setAgents] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    const tick = async () => {
      const a = await api.agents()
      setAgents(Array.isArray(a) ? a : [])
      setLastUpdated(new Date())
    }
    tick()
    const id = setInterval(tick, 3000)
    return () => clearInterval(id)
  }, [])

  const states = agents.reduce((acc, a) => {
    const s = (a.state || 'idle').toLowerCase()
    acc[s] = (acc[s] || 0) + 1
    return acc
  }, {})

  const totalIdle = states.idle || 0
  const totalBusy = states.busy || states.running || 0
  const totalErr = states.error || states.failed || 0

  return (
    <section className="panel" aria-label="Agent Cards">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21v-1a8 8 0 0 1 16 0v1" />
            </svg>
          </span>
          Agents
        </div>
        <span className="panel-meta">
          {agents.length} total · idle {totalIdle} · busy {totalBusy} · err {totalErr}
        </span>
      </div>

      {agents.length === 0 ? (
        <div className="search-empty">
          {lastUpdated ? 'No agents registered yet.' : 'Loading agents...'}
        </div>
      ) : (
        <div className="grid-dense">
          {agents.map(a => {
            const state = (a.state || 'idle').toLowerCase()
            const cls = STATE_CLASS[state] || 'idle'
            return (
              <article key={a.agent_id || a.id} className={`agent-card ${cls}`}>
                <div className="agent-card-header">
                  <span className="agent-id">{a.agent_id || a.id || 'agent'}</span>
                  <span className={`agent-state ${cls}`}>{state}</span>
                </div>
                {a.current_task ? (
                  <div className="agent-task" title={a.current_task}>{a.current_task}</div>
                ) : null}
                <div className="agent-meta">
                  <span>↑ {fmtAgo(a.last_active || a.updated_at)}</span>
                  {a.tasks_completed !== undefined ? (
                    <span>{a.tasks_completed} done</span>
                  ) : null}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
