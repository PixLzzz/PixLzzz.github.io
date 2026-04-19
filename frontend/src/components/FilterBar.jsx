import { useMemo, useCallback } from 'react'

const SOURCES = [
  { value: 'all', label: 'All sources' },
  { value: 'centris', label: 'Centris', color: 'var(--centris)' },
  { value: 'duproprio', label: 'DuProprio', color: 'var(--duproprio)' },
]

const SORTS = [
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
  { value: 'newest', label: 'Newest first' },
]

function fmt(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  return Math.round(n / 1000) + 'k'
}

function PriceRangeSlider({ min, max, value, onChange }) {
  const step = 10000
  const pctMin = ((value[0] - min) / (max - min)) * 100
  const pctMax = ((value[1] - min) / (max - min)) * 100

  const handleMin = useCallback((e) => {
    const v = Math.min(Number(e.target.value), value[1] - step)
    onChange([v, value[1]])
  }, [value, onChange, step])

  const handleMax = useCallback((e) => {
    const v = Math.max(Number(e.target.value), value[0] + step)
    onChange([value[0], v])
  }, [value, onChange, step])

  return (
    <div style={sliderStyles.wrapper}>
      <span style={sliderStyles.label}>{fmt(value[0])} $</span>
      <div style={sliderStyles.track}>
        <div
          style={{
            ...sliderStyles.fill,
            left: pctMin + '%',
            width: (pctMax - pctMin) + '%',
          }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value[0]}
          onChange={handleMin}
          style={sliderStyles.input}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value[1]}
          onChange={handleMax}
          style={sliderStyles.input}
        />
      </div>
      <span style={sliderStyles.label}>{fmt(value[1])} $</span>
    </div>
  )
}

export default function FilterBar({ source, sort, terrasse, recency, priceRange, listings, onSource, onSort, onTerrasse, onRecency, onPriceRange, count }) {
  const { absMin, absMax } = useMemo(() => {
    if (!listings || listings.length === 0) return { absMin: 0, absMax: 1000000 }
    const prices = listings.map(l => l.price).filter(p => p > 0)
    if (prices.length === 0) return { absMin: 0, absMax: 1000000 }
    const lo = Math.floor(Math.min(...prices) / 10000) * 10000
    const hi = Math.ceil(Math.max(...prices) / 10000) * 10000
    return { absMin: lo, absMax: hi }
  }, [listings])

  const effectiveRange = [
    priceRange[0] === 0 ? absMin : Math.max(priceRange[0], absMin),
    priceRange[1] === Infinity ? absMax : Math.min(priceRange[1], absMax),
  ]

  const isFiltered = effectiveRange[0] > absMin || effectiveRange[1] < absMax

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

      <div style={styles.priceRow}>
        <span style={styles.priceLabel}>Prix{isFiltered ? '' : ' (tout)'}</span>
        <PriceRangeSlider
          min={absMin}
          max={absMax}
          value={effectiveRange}
          onChange={onPriceRange}
        />
        {isFiltered && (
          <button
            style={styles.resetBtn}
            onClick={() => onPriceRange([0, Infinity])}
          >
            Reset
          </button>
        )}
      </div>
    </div>
  )
}

const sliderStyles = {
  wrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    flex: 1,
    minWidth: 200,
    maxWidth: 400,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text)',
    minWidth: 48,
    textAlign: 'center',
    whiteSpace: 'nowrap',
  },
  track: {
    position: 'relative',
    flex: 1,
    height: 6,
    borderRadius: 3,
    background: 'var(--surface2)',
  },
  fill: {
    position: 'absolute',
    top: 0,
    height: '100%',
    borderRadius: 3,
    background: 'var(--accent)',
    pointerEvents: 'none',
  },
  input: {
    position: 'absolute',
    top: -6,
    left: 0,
    width: '100%',
    height: 18,
    margin: 0,
    padding: 0,
    appearance: 'none',
    WebkitAppearance: 'none',
    background: 'transparent',
    pointerEvents: 'none',
    cursor: 'pointer',
    // Thumb styling is done via CSS below
  },
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
  priceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    paddingTop: 4,
  },
  priceLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--muted)',
    whiteSpace: 'nowrap',
  },
  resetBtn: {
    fontSize: 11,
    color: 'var(--muted)',
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '2px 10px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
}
