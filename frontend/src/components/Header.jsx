import { useState } from 'react'
import axios from 'axios'

const SOURCE_COLORS = {
  centris: 'var(--centris)',
  duproprio: 'var(--duproprio)',
}

export default function Header({ stats, scrapeStatus, onScrapeStart, staticMode = false }) {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleScrape() {
    setLoading(true)
    setMsg('')
    try {
      await axios.post('/api/scrape')
      setMsg('Scraping started — refresh in ~2 minutes')
      onScrapeStart()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Error starting scrape')
    } finally {
      setLoading(false)
    }
  }

  const lastRun = scrapeStatus?.last_run
    ? new Date(scrapeStatus.last_run + 'Z').toLocaleString('fr-CA', { timeZone: 'America/Toronto' })
    : null

  return (
    <header style={styles.header}>
      <div style={styles.top}>
        <div>
          <h1 style={styles.title}>AppartClaude</h1>
          <p style={styles.subtitle}>
            Plateau-Mont-Royal &amp; Mile-End &nbsp;·&nbsp; 500 000 $ – 750 000 $ &nbsp;·&nbsp; 2+ ch
          </p>
        </div>

        <div style={styles.actions}>
          {msg && <span style={styles.msg}>{msg}</span>}
          {!staticMode && (
            <button
              style={{ ...styles.btn, opacity: loading ? 0.6 : 1 }}
              onClick={handleScrape}
              disabled={loading || scrapeStatus?.running}
            >
              {scrapeStatus?.running ? '⟳ Scraping…' : loading ? 'Starting…' : 'Scrape now'}
            </button>
          )}
        </div>
      </div>

      <div style={styles.statsRow}>
        <div style={styles.statChip}>
          <span style={styles.statNum}>{stats?.total ?? 0}</span>
          <span style={styles.statLabel}>total listings</span>
        </div>
        {['centris', 'duproprio'].map((src) => (
          <div key={src} style={styles.statChip}>
            <span style={{ ...styles.dot, background: SOURCE_COLORS[src] }} />
            <span style={styles.statNum}>{stats?.by_source?.[src] ?? 0}</span>
            <span style={styles.statLabel}>{src}</span>
          </div>
        ))}
        {lastRun && (
          <div style={styles.statChip}>
            <span style={styles.statLabel}>Last scrape: {lastRun}</span>
          </div>
        )}
      </div>
    </header>
  )
}

const styles = {
  header: {
    background: 'var(--surface)',
    borderBottom: '1px solid var(--border)',
    padding: '20px 24px 0',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  top: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 16,
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    letterSpacing: '-0.5px',
    color: 'var(--text)',
  },
  subtitle: {
    color: 'var(--muted)',
    marginTop: 2,
    fontSize: 13,
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexShrink: 0,
  },
  btn: {
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '8px 18px',
    fontWeight: 600,
    fontSize: 14,
    transition: 'opacity 0.15s',
  },
  msg: {
    fontSize: 13,
    color: 'var(--muted)',
  },
  statsRow: {
    display: 'flex',
    gap: 8,
    paddingBottom: 12,
    flexWrap: 'wrap',
  },
  statChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 20,
    padding: '4px 12px',
  },
  statNum: {
    fontWeight: 700,
    fontSize: 15,
  },
  statLabel: {
    color: 'var(--muted)',
    fontSize: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    display: 'inline-block',
  },
}
