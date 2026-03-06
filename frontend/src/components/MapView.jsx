import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

import iconUrl from 'leaflet/dist/images/marker-icon.png'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

// Forces Leaflet to recalculate its container size after React renders
function InvalidateSize() {
  const map = useMap()
  useEffect(() => {
    map.invalidateSize()
  }, [map])
  return null
}

function fmt(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('fr-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 0,
  }).format(price)
}

const MONTREAL = [45.5017, -73.5673]

export default function MapView({ listings }) {
  const mapped = listings.filter(l => l.latitude && l.longitude)

  return (
    <div style={{ position: 'relative', height: 'calc(100vh - 200px)', minHeight: 450 }}>
      {mapped.length === 0 && (
        <div style={styles.notice}>
          Aucune annonce avec coordonnées.{' '}
          <button
            style={styles.btn}
            onClick={async () => {
              await fetch('/api/geocode/run', { method: 'POST' })
              alert('Géocodage démarré — rafraîchis dans quelques minutes.')
            }}
          >
            Géocoder maintenant
          </button>
        </div>
      )}
      <MapContainer
        center={MONTREAL}
        zoom={12}
        style={{ width: '100%', height: '100%' }}
      >
        <InvalidateSize />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {mapped.map(l => (
          <Marker key={l.id} position={[l.latitude, l.longitude]}>
            <Popup>
              <div style={styles.popup}>
                {l.image_url && (
                  <img src={l.image_url} alt="" style={styles.popupImg} />
                )}
                <div style={styles.popupPrice}>{fmt(l.price)}</div>
                <div style={styles.popupAddress}>{l.address || l.title}</div>
                {l.neighborhood && (
                  <div style={styles.popupNeighborhood}>{l.neighborhood}</div>
                )}
                <div style={styles.popupFeatures}>
                  {l.bedrooms > 0 && <span>🛏 {l.bedrooms}</span>}
                  {l.bathrooms > 0 && <span>🚿 {l.bathrooms}</span>}
                  {l.area_sqft > 0 && <span>📐 {Math.round(l.area_sqft)} pi²</span>}
                </div>
                <a href={l.url} target="_blank" rel="noopener noreferrer" style={styles.popupLink}>
                  Voir l'annonce →
                </a>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}

const styles = {
  notice: {
    position: 'absolute',
    top: 12,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 1000,
    background: 'rgba(20,20,30,0.92)',
    color: '#fff',
    padding: '10px 16px',
    borderRadius: 8,
    fontSize: 13,
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    whiteSpace: 'nowrap',
  },
  btn: {
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
  },
  popup: {
    minWidth: 180,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    color: '#111',
  },
  popupImg: {
    width: '100%',
    height: 110,
    objectFit: 'cover',
    borderRadius: 4,
    marginBottom: 2,
  },
  popupPrice: {
    fontSize: 16,
    fontWeight: 700,
  },
  popupAddress: {
    fontSize: 12,
    color: '#444',
    lineHeight: 1.3,
  },
  popupNeighborhood: {
    fontSize: 11,
    color: '#666',
    fontWeight: 500,
  },
  popupFeatures: {
    display: 'flex',
    gap: 8,
    fontSize: 12,
    marginTop: 2,
  },
  popupLink: {
    marginTop: 6,
    fontSize: 12,
    color: '#2563eb',
    fontWeight: 600,
    textDecoration: 'none',
  },
}
