const SOURCE_META = {
  centris:   { label: 'Centris',   color: 'var(--centris)' },
  duproprio: { label: 'DuProprio', color: 'var(--duproprio)' },
  remax:     { label: 'RE/MAX',    color: 'var(--remax)' },
}

function fmt(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(price)
}

export default function ListingCard({ listing }) {
  const src = SOURCE_META[listing.source] || { label: listing.source, color: '#888' }
  const hasImg = listing.image_url && !listing.image_url.startsWith('data:')

  return (
    <a href={listing.url} target="_blank" rel="noopener noreferrer" style={styles.card}>
      <div style={styles.imgWrap}>
        {hasImg ? (
          <img src={listing.image_url} alt={listing.title || listing.address} style={styles.img} />
        ) : (
          <div style={styles.imgPlaceholder}>
            <span style={{ fontSize: 32 }}>🏠</span>
          </div>
        )}
        <span style={{ ...styles.badge, background: src.color }}>{src.label}</span>
        {listing.has_terrace && (
          <span style={styles.terrasseBadge}>Terrasse</span>
        )}
      </div>

      <div style={styles.body}>
        <div style={styles.price}>{fmt(listing.price)}</div>

        <div style={styles.address}>
          {listing.address || listing.title || 'No address'}
        </div>

        {listing.neighborhood && (
          <div style={styles.neighborhood}>{listing.neighborhood}</div>
        )}

        <div style={styles.features}>
          {listing.bedrooms > 0 && (
            <span style={styles.feature}>
              <span style={styles.featureIcon}>🛏</span> {listing.bedrooms} ch
            </span>
          )}
          {listing.bathrooms > 0 && (
            <span style={styles.feature}>
              <span style={styles.featureIcon}>🚿</span> {listing.bathrooms} sdb
            </span>
          )}
          {listing.area_sqft > 0 && (
            <span style={styles.feature}>
              <span style={styles.featureIcon}>📐</span> {Math.round(listing.area_sqft)} pi²
            </span>
          )}
        </div>

        {listing.first_seen && (
          <div style={styles.date}>
            Added {new Date(listing.first_seen + 'Z').toLocaleDateString('fr-CA')}
          </div>
        )}
      </div>
    </a>
  )
}

const styles = {
  card: {
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    overflow: 'hidden',
    transition: 'transform 0.15s, border-color 0.15s',
    cursor: 'pointer',
    textDecoration: 'none',
    color: 'inherit',
  },
  imgWrap: {
    position: 'relative',
    height: 180,
    background: 'var(--surface2)',
    flexShrink: 0,
  },
  img: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: 'block',
  },
  imgPlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--surface2)',
  },
  badge: {
    position: 'absolute',
    top: 10,
    left: 10,
    color: '#fff',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.5px',
    padding: '3px 8px',
    borderRadius: 20,
    textTransform: 'uppercase',
  },
  terrasseBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    background: 'rgba(0,0,0,0.55)',
    color: '#fff',
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 20,
  },
  body: {
    padding: '14px 16px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    flex: 1,
  },
  price: {
    fontSize: 20,
    fontWeight: 700,
    letterSpacing: '-0.5px',
    color: 'var(--text)',
  },
  address: {
    fontSize: 13,
    color: 'var(--muted)',
    lineHeight: 1.4,
  },
  neighborhood: {
    fontSize: 12,
    color: 'var(--accent)',
    fontWeight: 500,
  },
  features: {
    display: 'flex',
    gap: 12,
    marginTop: 4,
  },
  feature: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 13,
    color: 'var(--text)',
    fontWeight: 500,
  },
  featureIcon: {
    fontSize: 14,
  },
  date: {
    fontSize: 11,
    color: 'var(--muted)',
    marginTop: 4,
  },
}
