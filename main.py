"""AppartClaude — FastAPI backend."""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import inspect, text

from config import CRITERIA
from database import Base, engine, get_db
from models import Listing
from scrapers.centris import CentrisScraper
from scrapers.duproprio import DuProprioScraper
from scrapers.remax import RemaxScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Add columns introduced after the initial schema (non-destructive migration)
_NEW_COLUMNS = [
    ("image_url",    "ALTER TABLE listings ADD COLUMN image_url VARCHAR(1000)"),
    ("description",  "ALTER TABLE listings ADD COLUMN description TEXT"),
    ("has_terrace",  "ALTER TABLE listings ADD COLUMN has_terrace BOOLEAN DEFAULT 0"),
    ("is_active",    "ALTER TABLE listings ADD COLUMN is_active BOOLEAN DEFAULT 1"),
    ("latitude",     "ALTER TABLE listings ADD COLUMN latitude FLOAT"),
    ("longitude",    "ALTER TABLE listings ADD COLUMN longitude FLOAT"),
    ("last_seen",    "ALTER TABLE listings ADD COLUMN last_seen DATETIME"),
]
with engine.connect() as _conn:
    _existing = {col["name"] for col in inspect(engine).get_columns("listings")}
    for _col, _ddl in _NEW_COLUMNS:
        if _col not in _existing:
            _conn.execute(text(_ddl))
            logger.info("Migration: added column %s", _col)
    _conn.commit()

app = FastAPI(title="AppartClaude API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory scrape status
scrape_status = {
    "running": False,
    "last_run": None,
    "last_counts": {},
    "last_error": None,
}


# ---------- Schemas ----------

class ListingOut(BaseModel):
    id: int
    title: Optional[str]
    price: float
    address: Optional[str]
    neighborhood: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    area_sqft: Optional[float]
    source: Optional[str]
    url: str
    image_url: Optional[str]
    description: Optional[str]
    has_terrace: Optional[bool]
    latitude: Optional[float]
    longitude: Optional[float]
    first_seen: Optional[datetime]

    class Config:
        from_attributes = True


class ScrapeStatus(BaseModel):
    running: bool
    last_run: Optional[datetime]
    last_counts: dict
    last_error: Optional[str]


# ---------- Helpers ----------

def _clean_address_for_geocoding(address: str) -> str:
    """Strip parenthetical neighborhood tags and unit numbers for cleaner geocoding."""
    import re
    # Remove parenthetical parts like (Le Plateau-Mont-Royal) (La Petite-Patrie)
    cleaned = re.sub(r"\s*\([^)]*\)", "", address)
    # Remove unit/app numbers (e.g. "app. 409", "app. #5", "#302")
    cleaned = re.sub(r"\s*(app\.?\s*#?\d+\w*|#\d+\w*)", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().strip(",").strip()


async def _geocode(address: str) -> tuple[float, float] | tuple[None, None]:
    """Geocode an address using Nominatim (OpenStreetMap). Returns (lat, lng) or (None, None)."""
    if not address:
        return None, None
    clean = _clean_address_for_geocoding(address)
    query = f"{clean}, Montreal, Quebec, Canada"
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"format": "json", "q": query, "limit": 1},
                    headers={"User-Agent": "AppartClaude/1.0"},
                )
                if resp.status_code == 429:
                    logger.warning(f"Nominatim rate-limited (attempt {attempt+1}), waiting 5s…")
                    await asyncio.sleep(5)
                    continue
                results = resp.json()
                if results:
                    return float(results[0]["lat"]), float(results[0]["lon"])
                return None, None
        except Exception as e:
            logger.warning(f"Geocoding failed for '{address}': {e}")
    return None, None


async def _upsert_listing(db: Session, data: dict) -> bool:
    """Insert or update a listing by URL. Returns True if new."""
    existing = db.query(Listing).filter(Listing.url == data["url"]).first()
    if existing:
        existing.price = data["price"]
        existing.title = data["title"]
        existing.bedrooms = data["bedrooms"]
        existing.bathrooms = data["bathrooms"]
        existing.area_sqft = data["area_sqft"]
        existing.image_url = data["image_url"]
        existing.description = data.get("description", "")
        existing.has_terrace = data.get("has_terrace", False)
        existing.is_active = True
        # Backfill coordinates from scraper if missing
        if not existing.latitude and data.get("latitude"):
            existing.latitude = data["latitude"]
            existing.longitude = data.get("longitude")
        return False
    # Use pre-provided coordinates (e.g. from RE/MAX API), fall back to Nominatim
    lat = data.pop("latitude", None)
    lng = data.pop("longitude", None)
    if not lat or not lng:
        lat, lng = await _geocode(data.get("address", ""))
    db.add(Listing(**data, latitude=lat, longitude=lng))
    return True


def _matches_criteria(listing: dict) -> bool:
    """Apply price range and min_bedrooms filter."""
    price = listing.get("price", 0)
    bedrooms = listing.get("bedrooms", 0)
    if price and price > CRITERIA["max_price"]:
        return False
    if price and price < CRITERIA["min_price"]:
        return False
    if bedrooms and bedrooms < CRITERIA["min_bedrooms"]:
        return False
    return True


async def _run_scrape():
    """Background task: run all scrapers and persist results."""
    global scrape_status
    scrape_status["running"] = True
    scrape_status["last_error"] = None
    counts = {}

    try:
        scrapers = [
            ("centris", CentrisScraper()),
            ("duproprio", DuProprioScraper()),
            ("remax", RemaxScraper()),
        ]

        db = next(get_db())
        try:
            for name, scraper in scrapers:
                try:
                    raw = await scraper.scrape()
                    kept = [r for r in raw if _matches_criteria(r)]
                    new_count = 0
                    for item in kept:
                        is_new = await _upsert_listing(db, item)
                        if is_new:
                            new_count += 1
                            await asyncio.sleep(1.1)  # Nominatim rate limit: 1 req/s
                    db.commit()
                    counts[name] = {"total": len(kept), "new": new_count}
                    logger.info(f"{name}: {len(kept)} kept, {new_count} new")
                except Exception as e:
                    logger.error(f"Scraper {name} failed: {e}")
                    counts[name] = {"total": 0, "new": 0, "error": str(e)}
        finally:
            db.close()
    except Exception as e:
        scrape_status["last_error"] = str(e)
        logger.error(f"Scrape run error: {e}")
    finally:
        scrape_status["running"] = False
        scrape_status["last_run"] = datetime.utcnow()
        scrape_status["last_counts"] = counts


# ---------- Endpoints ----------


@app.get("/")
def root():
    return {"app": "AppartClaude", "version": "1.0.0", "criteria": CRITERIA}


@app.get("/listings", response_model=List[ListingOut])
def get_listings(
    source: Optional[str] = None,
    sort: str = "price_asc",
    db: Session = Depends(get_db),
):
    """Return all saved listings, optionally filtered by source."""
    query = db.query(Listing).filter(Listing.is_active == True)

    if source and source != "all":
        query = query.filter(Listing.source == source)

    if sort == "price_asc":
        query = query.order_by(Listing.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Listing.price.desc())
    elif sort == "newest":
        query = query.order_by(Listing.first_seen.desc())
    else:
        query = query.order_by(Listing.price.asc())

    return query.all()


@app.post("/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Trigger a background scrape of all sources."""
    if scrape_status["running"]:
        raise HTTPException(status_code=409, detail="Scrape already running")
    background_tasks.add_task(_run_scrape)
    return {"message": "Scrape started in background"}


@app.get("/scrape/status", response_model=ScrapeStatus)
def get_scrape_status():
    return scrape_status


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Count listings per source."""
    from sqlalchemy import func
    rows = (
        db.query(Listing.source, func.count(Listing.id))
        .filter(Listing.is_active == True)
        .group_by(Listing.source)
        .all()
    )
    total = sum(c for _, c in rows)
    return {
        "total": total,
        "by_source": {src: cnt for src, cnt in rows},
        "criteria": CRITERIA,
    }


@app.post("/geocode/run")
async def run_geocode(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Geocode existing listings that have no coordinates."""
    pending = db.query(Listing).filter(
        Listing.is_active == True,
        Listing.latitude == None,
        Listing.address != None,
    ).all()

    async def _do_geocode():
        _db = next(get_db())
        try:
            for listing in pending:
                lat, lng = await _geocode(listing.address)
                if lat:
                    _db.query(Listing).filter(Listing.id == listing.id).update(
                        {"latitude": lat, "longitude": lng}
                    )
                    _db.commit()
                    await asyncio.sleep(1.1)
        finally:
            _db.close()

    background_tasks.add_task(_do_geocode)
    return {"message": f"Geocoding {len(pending)} listings in background"}


@app.delete("/listings/purge")
def purge_listings(db: Session = Depends(get_db)):
    """Delete all listings (reset). Use carefully."""
    count = db.query(Listing).delete()
    db.commit()
    return {"deleted": count}


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=True)
