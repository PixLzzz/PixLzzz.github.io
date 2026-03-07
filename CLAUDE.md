# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

The project lives in WSL Ubuntu (`/home/pixl/Dev/AppartClaude`) accessed from a Windows host via the UNC path `\\wsl$\Ubuntu\home\pixl\Dev\AppartClaude`. **The Bash tool does not work for WSL commands** — use the `preview_start` / `preview_eval` mechanism (via `.claude/launch.json`) to run shell commands inside WSL.

## Running the project

Both servers are configured in `.claude/launch.json` and started with `preview_start`:

| Server | Name in launch.json | Port |
|--------|---------------------|------|
| FastAPI backend | `backend` | 8001 |
| Vite frontend | `frontend` | 5174 |

Manual commands (run inside WSL):
```bash
# Backend
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend && npm run dev -- --host

# Export DB snapshot for GitHub Pages
python3 export_data.py

# Deploy to GitHub Pages (builds + pushes gh-pages branch)
cd frontend && npm run deploy
```

First-time Playwright setup (WSL):
```bash
venv/bin/playwright install chromium
```

## Architecture

### Backend (`/`)
- **`main.py`** — FastAPI app. Endpoints: `GET /listings`, `GET /stats`, `POST /scrape`, `GET /scrape/status`, `POST /geocode/run`, `DELETE /listings/purge`.
- **`config.py`** — Hardcoded search criteria (price 500k–750k CAD, 2+ bedrooms, Plateau-Mont-Royal / Mile-End). Edit here to change what gets scraped.
- **`database.py`** — SQLite via SQLAlchemy. DB file: `appartclaude.db`. Connection string: `sqlite:///./appartclaude.db`.
- **`models.py`** — Single `Listing` model.
- **`scrapers/`** — Playwright-based scrapers. `BaseScraper` (ABC) provides `_parse_price/int/area` helpers. Each scraper (`centris.py`, `duproprio.py`, `remax.py`) implements `async scrape() -> List[Dict]`. Centris and DuProprio are the primary sources; RE/MAX results appear under the `centris` source per QC law.
- **`export_data.py`** — Reads SQLite → writes `frontend/public/data.json` for static deployments. Auto-re-execs itself with `venv/bin/python3` if run with the system Python.

### Frontend (`/frontend`)
React 18 + Vite. All styling is inline (no CSS files). No routing library — single page.

- **`App.jsx`** — Root state: listings, stats, scrapeStatus, source filter, sort, terrasse/nouveau toggles, view (list/map). Polls every 5 s while a scrape is running.
- **`Header.jsx`** — Displays stats chips and the "Scrape now" button (hidden when `staticMode=true`).
- **`FilterBar.jsx`** — Source selector, sort dropdown, "Terrasse" and "Nouveau <7j" toggle chips.
- **`ListingCard.jsx`** — Grid card linking to the listing's source URL.
- **`MapView.jsx`** — Leaflet map. Uses explicit icon imports + `delete L.Icon.Default.prototype._getIconUrl` to fix Vite's doubled asset path bug. Popup shows image, price, address, beds/baths.

### Two deployment modes

| Mode | Trigger | Data source | Scrape button |
|------|---------|-------------|---------------|
| **Live** (local dev) | `VITE_STATIC` unset | FastAPI API at `/api` | Visible |
| **Static** (GitHub Pages) | `VITE_STATIC=true` | `public/data.json` | Hidden |

In static mode `App.jsx` fetches `import.meta.env.BASE_URL + 'data.json'` and performs sorting/filtering client-side.

### GitHub Pages deployment
- `.github/workflows/deploy.yml` — Builds with `VITE_STATIC=true` on every push to `main`, deploys `frontend/dist` to the `gh-pages` branch.
- `cron_scrape.sh` — WSL cron script (runs every 6 hours via `crontab`): starts backend if needed → triggers scrape → waits 3 min → runs `export_data.py` → `git commit && push`. The push triggers the Actions deploy.

## Key constraints

- **React 18 only** — `react-leaflet` is pinned to `^4.2.1`. v5 requires React 19 (`@react-leaflet/core` v3 imports the `use` hook).
- **SQLite migrations** — `Base.metadata.create_all()` does not ALTER existing tables. New columns must be added via the `_NEW_COLUMNS` list in `main.py` (runs at startup).
- **Nominatim rate limit** — Geocoding new listings sleeps 1.1 s between requests. Do not batch-geocode without the sleep.
- **Playwright in WSL** — `BaseScraper` injects `~/lib_extract/usr/lib/x86_64-linux-gnu` into `LD_LIBRARY_PATH` so Chromium can find `libnss3`. If Playwright fails to launch, check that `lib_extract` exists.
- **CORS** — Backend allows `localhost:5173`, `5174`, `3000`. Add origins in `main.py` if using a different port.
