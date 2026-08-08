import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import api from '../api/client.js'

export default function PipelineMonitor() {
  const [tasks, setTasks] = useState([])
  const [history, setHistory] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    const tick = async () => {
      const t = await api.tasks()
      setTasks(t)
      const buckets = { pending: 0, running: 0, completed: 0, failed: 0 }
      t.forEach(x => {
        buckets[x.status] = (buckets[x.status] || 0) + 1
      })
      setHistory(h => [...h.slice(-19), { t: Date.now(), ...buckets }])
      setLastUpdated(new Date())
    }
    tick()
    const id = setInterval(tick, 2000)
    return () => clearInterval(id)
  }, [])

  const last = history[history.length - 1] || {}
  const totalCompleted = last.completed || 0
  const totalFailed = last.failed || 0
  const total = totalCompleted + totalFailed
  const successRate = total > 0 ? Math.round((totalCompleted / total) * 100) : null
  const failedCount = totalFailed

  const stages = [
    { key: 'pending', label: 'Pending', count: last.pending || 0 },
    { key: 'running', label: 'Running', count: last.running || 0 },
    { key: 'completed', label: 'Completed', count: totalCompleted },
    { key: 'failed', label: 'Failed', count: totalFailed },
  ]
  const maxCount = Math.max.apply(null, stages.map(s => s.count).concat([1]))

  const rateClass = successRate === null
    ? ''
    : successRate >= 95 ? 'success' : successRate >= 80 ? 'warn' : 'err'
  const failedClass = failedCount > 0 ? 'err' : ''

  return (
    <section className="panel" aria-label="Pipeline Monitor">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18" />
              <path d="M7 14l4-4 4 4 5-5" />
            </svg>
          </span>
          Pipeline Monitor
        </div>
        <span className="panel-meta">
          {tasks.length} tasks · {lastUpdated ? Math.round((Date.now() - lastUpdated.getTime()) / 1000) + 's ago' : '—'}
        </span>
      </div>

      {successRate !== null ? (
        <div className="stat-row">
          <div className="stat">
            <span className="stat-label">Success Rate</span>
            <span className={'stat-value ' + rateClass}>{successRate}%</span>
          </div>
          <div className="stat">
            <span className="stat-label">Active</span>
            <span className="stat-value">{last.running || 0}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Throughput</span>
            <span className="stat-value">{totalCompleted}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Errors</span>
            <span className={'stat-value ' + failedClass}>{failedCount}</span>
          </div>
        </div>
      ) : null}

      <div className="pipeline-funnel" role="list">
        {stages.map(stage => {
          const pct = maxCount > 0 ? Math.round((stage.count / maxCount) * 100) : 0
          return (
            <div key={stage.key} className="pipeline-stage" role="listitem">
              <span className="pipeline-stage-name">{stage.label}</span>
              <div className="pipeline-stage-bar" aria-label={stage.label + ': ' + stage.count}>
                <div
                  className={'pipeline-stage-fill ' + stage.key}
                  style={{ width: pct + '%' }}
                  role="progressbar"
                  aria-valuenow={stage.count}
                  aria-valuemin="0"
                  aria-valuemax={maxCount}
                />
              </div>
              <span className="pipeline-stage-count">{stage.count}</span>
            </div>
          )
        })}
      </div>

      {history.length > 1 ? (
        <div style={{ height: 180, marginTop: 'var(--space-5)' }}>
          <ResponsiveContainer>
            <LineChart data={history}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <XAxis
                dataKey="t"
                tickFormatter={v => new Date(v).toLocaleTimeString().slice(0, 5)}
                stroke="#64748B"
                tick={{ fontSize: 11, fontFamily: 'Fira Code, monospace' }}
              />
              <YAxis
                stroke="#64748B"
                tick={{ fontSize: 11, fontFamily: 'Fira Code, monospace' }}
                width={32}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(15, 20, 36, 0.95)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontFamily: 'Fira Code, monospace',
                  fontSize: '12px',
                }}
                labelFormatter={v => new Date(v).toLocaleTimeString()}
              />
              <Line type="monotone" dataKey="completed" stroke="#10B981" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="running" stroke="#3B82F6" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="failed" stroke="#EF4444" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </section>
  )
}
