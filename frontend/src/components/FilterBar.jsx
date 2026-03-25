const SOURCES = [
  { value: 'all', label: 'All sources' },
  { value: 'centris', label: 'Centris (incl. RE/MAX)', color: 'var(--centris)' },
  { value: 'duproprio', label: 'DuProprio', color: 'var(--duproprio)' },
]

const SORTS = [
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
  { value: 'newest', label: 'Newest first' },
]

export default function FilterBar({ source, sort, terrasse, recency, onSource, onSort, onTerrasse, onRecency, count }) {
  return (
    <div style={styles.bar}>
      <div style={styles.group}>
        {SOURCES.map((s) => (
          <button
            key={s.value}
            style={{
              ...styles.chip,
              ...(source === s.value ? { ...styles.chipActive, borderColor: s.color || 'var(--accent)' } : {}),
            }}
            onClick={() => onSource(s.value)}
          >
            {s.color && <span style={{ ...styles.dot, background: s.color }} />}
            {s.label}
          </button>
        ))}
        <button
          style={{
            ...styles.chip,
            ...(terrasse ? { ...styles.chipActive, borderColor: 'var(--accent)' } : {}),
          }}
          onClick={onTerrasse}
        >
          Terrasse
        </button>
        <button
          style={{
            ...styles.chip,
            ...(recency === 7 ? { ...styles.chipActive, borderColor: '#f59e0b' } : {}),
          }}
          onClick={() => onRecency(recency === 7 ? null : 7)}
        >
          {recency === 7 && <span style={{ ...styles.dot, background: '#f59e0b' }} />}
          Nouveau &lt;7j
        </button>
        <button
          style={{
            ...styles.chip,
            ...(recency === 3 ? { ...styles.chipActive, borderColor: '#ef4444' } : {}),
          }}
          onClick={() => onRecency(recency === 3 ? null : 3)}
        >
          {recency === 3 && <span style={{ ...styles.dot, background: '#ef4444' }} />}
          Nouveau &lt;3j
        </button>
        <span style={styles.remaxNote}>* RE/MAX QC listings are on Centris by law</span>
      </div>

      <div style={styles.right}>
        <span style={styles.count}>{count} listing{count !== 1 ? 's' : ''}</span>
        <select style={styles.select} value={sort} onChange={(e) => onSort(e.target.value)}>
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

const styles = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 24px',
    borderBottom: '1px solid var(--border)',
    flexWrap: 'wrap',
    gap: 12,
  },
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  chip: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 20,
    padding: '5px 14px',
    color: 'var(--muted)',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  chipActive: {
    background: 'var(--surface)',
    color: 'var(--text)',
    borderWidth: 2,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  remaxNote: {
    fontSize: 11,
    color: 'var(--muted)',
    fontStyle: 'italic',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  count: {
    color: 'var(--muted)',
    fontSize: 13,
  },
  select: {
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '6px 10px',
    fontSize: 13,
    cursor: 'pointer',
  },
}
