import { useState } from 'react'
import api from '../api/client.js'

export default function VaultSearch() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const search = async (e) => {
    e?.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const r = await api.vault(q)
      setResults(Array.isArray(r) ? r : [])
    } catch {
      setResults([])
    }
    setLoading(false)
  }

  return (
    <section className="panel" aria-label="Vault Search">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.35-4.35" />
         </svg>
       </span>
          Vault Search
     </div>
        <span className="panel-meta">{results.length} results</span>
   </div>

      <form className="search-bar" onSubmit={search}>
        <input
          type="search"
          className="search-input"
          placeholder="Search vault entries..."
          value={q}
          onChange={e => setQ(e.target.value)}
          aria-label="Search query"
        />
        <button type="submit" className="btn" disabled={loading || !q.trim()}>
          {loading ? 'Searching...' : 'Search'}
     </button>
   </form>

      {searched && results.length === 0 && !loading && (
        <div className="search-empty">No matches for "{q}".</div>
      )}

      {!searched && (
        <div className="search-empty">Enter a query to search the vault</div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          {results.map((r, i) => (
            <div key={i} className="search-result">
              {typeof r === 'string' ? r : JSON.stringify(r)}
         </div>
          ))}
     </div>
      )}
 </section>
  )
}
