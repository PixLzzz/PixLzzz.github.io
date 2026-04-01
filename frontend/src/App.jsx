import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import Header from './components/Header'
import FilterBar from './components/FilterBar'
import ListingCard from './components/ListingCard'
import MapView from './components/MapView'

// If VITE_API_URL is set, use it as the backend; otherwise use the Vite dev proxy.
// When neither is available (GitHub Pages), STATIC_MODE kicks in and data.json is used.
const API = import.meta.env.VITE_API_URL || '/api'
const STATIC_MODE = import.meta.env.VITE_STATIC === 'true'

/** Compute stats locally from a listings array (used in static mode). */
function computeStats(listings) {
  const by_source = {}
  for (const l of listings) {
    by_source[l.source] = (by_source[l.source] || 0) + 1
  }
  return { total: listings.length, by_source }
}

export default function App() {
  const [listings, setListings] = useState([])
  const [stats, setStats] = useState(null)
  const [scrapeStatus, setScrapeStatus] = useState(null)
  const [source, setSource] = useState('all')
  const [sort, setSort] = useState('price_asc')
  const [terrasse, setTerrasse] = useState(false)
  const [recency, setRecency] = useState(null) // null | 7 | 3
  const [priceRange, setPriceRange] = useState([0, Infinity])
  const [view, setView] = useState('list') // 'list' | 'map'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      if (STATIC_MODE) {
        // GitHub Pages: load pre-exported snapshot
        const res = await fetch(import.meta.env.BASE_URL + 'data.json')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        let all = await res.json()
        // Compute stats from ALL listings before filtering
        setStats(computeStats(all))
        // Client-side sort
        if (sort === 'price_asc')  all = [...all].sort((a, b) => a.price - b.price)
        if (sort === 'price_desc') all = [...all].sort((a, b) => b.price - a.price)
        if (sort === 'newest')     all = [...all].sort((a, b) => new Date(b.first_seen) - new Date(a.first_seen))
        if (source !== 'all')      all = all.filter(l => l.source === source)
        setListings(all)
        setScrapeStatus({ running: false, last_run: null })
      } else {
        const params = { sort }
        if (source !== 'all') params.source = source

        const [listRes, statsRes, statusRes] = await Promise.all([
          axios.get(`${API}/listings`, { params }),
          axios.get(`${API}/stats`),
          axios.get(`${API}/scrape/status`),
        ])
        const all = listRes.data
        setListings(all)
        setStats(statsRes.data)
        setScrapeStatus(statusRes.data)
      }
      setError(null)
    } catch (e) {
      setError(STATIC_MODE
        ? 'Could not load data.json — run export_data.py first.'
        : 'Cannot reach the API — is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [source, sort])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Poll while scraping is running
  useEffect(() => {
    if (!scrapeStatus?.running) return
    const id = setInterval(fetchAll, 5000)
    return () => clearInterval(id)
  }, [scrapeStatus?.running, fetchAll])

  const recencyCutoff = recency ? Date.now() - recency * 24 * 60 * 60 * 1000 : null
  const filtered = listings
    .filter(l => !terrasse || l.has_terrace)
    .filter(l => !recencyCutoff || (l.first_seen && new Date(l.first_seen) > recencyCutoff))
    .filter(l => l.price >= priceRange[0] && l.price <= priceRange[1])

  return (
    <div style={styles.app}>
      <Header
        stats={stats}
        scrapeStatus={scrapeStatus}
        onScrapeStart={fetchAll}
        staticMode={STATIC_MODE}
      />

      <FilterBar
        source={source}
        sort={sort}
        terrasse={terrasse}
        recency={recency}
        priceRange={priceRange}
        listings={listings}
        onSource={setSource}
        onSort={setSort}
        onTerrasse={() => setTerrasse(t => !t)}
        onRecency={setRecency}
        onPriceRange={setPriceRange}
        count={filtered.length}
      />

      <div style={styles.viewToggle}>
        <button
          style={{ ...styles.toggleBtn, ...(view === 'list' ? styles.toggleBtnActive : {}) }}
          onClick={() => setView('list')}
        >
          ☰ Liste
        </button>
        <button
          style={{ ...styles.toggleBtn, ...(view === 'map' ? styles.toggleBtnActive : {}) }}
          onClick={() => setView('map')}
        >
          🗺 Carte
        </button>
      </div>

      <main style={styles.main}>
        {error && (
          <div style={styles.error}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && !error && (
          <div style={styles.center}>Loading listings…</div>
        )}

        {!loading && !error && listings.length === 0 && (
          <div style={styles.empty}>
            <div style={styles.emptyIcon}>🏙️</div>
            <p>No listings yet.</p>
            <p style={{ color: 'var(--muted)', marginTop: 8 }}>
              Click <strong>Scrape now</strong> to fetch listings from Centris, DuProprio, and RE/MAX Quebec.
            </p>
          </div>
        )}

        {!loading && listings.length > 0 && view === 'list' && (
          <div style={styles.grid}>
            {filtered.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
        )}

        {!loading && listings.length > 0 && view === 'map' && (
          <MapView listings={filtered} />
        )}
      </main>
    </div>
  )
}

const styles = {
  app: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  main: {
    flex: 1,
    padding: '0 24px 24px',
  },
  viewToggle: {
    display: 'flex',
    gap: 8,
    padding: '0 24px 12px',
  },
  toggleBtn: {
    padding: '6px 16px',
    borderRadius: 20,
    border: '1px solid var(--border)',
    background: 'var(--surface)',
    color: 'var(--muted)',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  toggleBtnActive: {
    background: 'var(--accent)',
    color: '#fff',
    borderColor: 'var(--accent)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: 20,
  },
  center: {
    textAlign: 'center',
    padding: '60px 0',
    color: 'var(--muted)',
  },
  empty: {
    textAlign: 'center',
    padding: '80px 0',
    color: 'var(--text)',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  error: {
    background: '#2d1515',
    border: '1px solid #7f1d1d',
    borderRadius: 8,
    padding: '12px 16px',
    color: '#fca5a5',
    marginBottom: 20,
  },
}
