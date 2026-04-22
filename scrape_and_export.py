#!/usr/bin/env python3
"""
Standalone scrape + export for GitHub Actions.

No SQLite required. Reads the existing data.json as source of truth,
runs all scrapers, upserts by URL, writes updated data.json.

Usage:
    python scrape_and_export.py
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent

# Auto-use virtualenv when available (local runs)
_venv = ROOT / "venv" / "bin" / "python3"
if _venv.exists() and Path(sys.executable).resolve() != _venv.resolve():
    os.execv(str(_venv), [str(_venv)] + sys.argv)

sys.path.insert(0, str(ROOT))

import httpx
from config import CRITERIA
from scrapers.centris import CentrisScraper
from scrapers.duproprio import DuProprioScraper

DATA_JSON = ROOT / "frontend" / "public" / "data.json"
STATE_JSON = ROOT / "frontend" / "public" / "state.json"  # Full state (incl. inactive) for tracking


def clean_address(address: str) -> str:
    """Clean address for Nominatim geocoding."""
    addr = re.sub(r"\t+", " ", address)           # tabs → space
    addr = re.sub(r"\s{2,}", " ", addr).strip()    # collapse whitespace
    addr = re.sub(r"\s*\(.*?\)\s*$", "", addr)     # remove trailing "(Le Plateau-Mont-Royal)"
    # Remove "apt." / "app." with any suffix (A, B, PH11, A102, 101-102, etc.)
    addr = re.sub(r",?\s*(?:apt|app|unit[ée]?)\.?\s*[A-Za-z0-9-]+", "", addr, flags=re.IGNORECASE)
    # Remove trailing neighborhood/city (", Le Plateau-Mont-Royal", ", Montréal", etc.)
    addr = re.sub(r",\s*(?:Le |La |L')?(?:Plateau|Rosemont|Petite-Patrie|Montr[ée]al|Mile[ -]End|Beaubien).*$", "", addr, flags=re.IGNORECASE)
    # Civic number: "A-2187" or "109-5400" → keep the larger number (street number)
    addr = re.sub(r"^[A-Za-z]+-(\d+)", r"\1", addr)           # A-2187 → 2187
    addr = re.sub(r"^(\d+)-(\d{3,})", r"\2", addr)            # 109-5400 → 5400
    # Remove letter suffix from civic numbers: "6872Z" → "6872"
    addr = re.sub(r"^(\d+)[A-Za-z],", r"\1,", addr)
    return addr.strip()


async def geocode(address: str) -> tuple:
    if not address:
        return None, None
    cleaned = clean_address(address)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"format": "json", "q": f"{cleaned}, Montreal, Quebec, Canada", "limit": 1},
                headers={"User-Agent": "AppartClaude/1.0"},
            )
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"  geocode error for '{cleaned}': {e}")
    return None, None


def matches_criteria(item: dict) -> bool:
    price = item.get("price", 0)
    beds = item.get("bedrooms", 0)
    if price and price > CRITERIA["max_price"]:
        return False
    if price and price < CRITERIA["min_price"]:
        return False
    if beds and beds < CRITERIA["min_bedrooms"]:
        return False
    return True


async def main():
    # Load existing snapshot keyed by URL (includes inactive listings)
    existing: dict[str, dict] = {}
    # Prefer state.json (has inactive listings) over data.json (active only)
    src = STATE_JSON if STATE_JSON.exists() else DATA_JSON
    if src.exists():
        try:
            for item in json.loads(src.read_text(encoding="utf-8")):
                existing[item["url"]] = item
            print(f"Loaded {len(existing)} listings from {src.name}")
        except Exception as e:
            print(f"Warning: could not read {src.name}: {e}")

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    new_count = 0
    seen_urls: set[str] = set()           # URLs found in this scrape run
    succeeded_sources: set[str] = set()   # Scrapers that ran without error

    for name, scraper in [
        ("centris",   CentrisScraper()),
        ("duproprio", DuProprioScraper()),
    ]:
        try:
            raw = await scraper.scrape()
            kept = [r for r in raw if matches_criteria(r)]
            print(f"{name}: {len(raw)} scraped, {len(kept)} match criteria")
            succeeded_sources.add(name)

            for item in kept:
                url = item["url"]
                seen_urls.add(url)
                if url in existing:
                    # Preserve first_seen, update everything else
                    existing[url].update({
                        "price":       item["price"],
                        "title":       item.get("title"),
                        "bedrooms":    item.get("bedrooms"),
                        "bathrooms":   item.get("bathrooms"),
                        "area_sqft":   item.get("area_sqft"),
                        "image_url":   item.get("image_url"),
                        "description": item.get("description", ""),
                        "has_terrace": item.get("has_terrace", False),
                        "is_active":   True,
                        "last_seen":   now,
                    })
                else:
                    lat, lng = await geocode(item.get("address", ""))
                    await asyncio.sleep(1.1)  # Nominatim: 1 req/s
                    existing[url] = {
                        **item,
                        "is_active":  True,
                        "latitude":   lat,
                        "longitude":  lng,
                        "first_seen": now,
                        "last_seen":  now,
                    }
                    new_count += 1
                    print(f"  + New: {item.get('address', url[:70])}")

        except Exception as e:
            import traceback
            print(f"ERROR: {name} scraper failed: {e}")
            traceback.print_exc()

    # Mark listings as inactive if their source scraper succeeded but didn't find them,
    # or if their source no longer has a scraper at all
    active_sources = {name for name, _ in [("centris", None), ("duproprio", None)]}
    stale_count = 0
    for url, item in existing.items():
        src = item.get("source")
        if url not in seen_urls and (src in succeeded_sources or src not in active_sources):
            item["is_active"] = False
            stale_count += 1
    if stale_count:
        print(f"\n⏸ Marked {stale_count} listings as inactive (not found in latest scrape)")

    # Permanently delete listings inactive for more than 3 days
    cutoff = (now_dt - timedelta(days=3)).isoformat()
    expired = [
        url for url, item in existing.items()
        if not item.get("is_active", True) and item.get("last_seen", now) < cutoff
    ]
    for url in expired:
        del existing[url]
    if expired:
        print(f"🗑 Removed {len(expired)} listings inactive for 3+ days")

    # Retroactively geocode listings that have null coordinates
    missing_geo = [
        v for v in existing.values()
        if v.get("is_active") and (not v.get("latitude") or not v.get("longitude"))
    ]
    if missing_geo:
        print(f"\nGeocoding {len(missing_geo)} listings with missing coordinates…")
        for item in missing_geo:
            lat, lng = await geocode(item.get("address", ""))
            await asyncio.sleep(1.1)  # Nominatim: 1 req/s
            item["latitude"] = lat
            item["longitude"] = lng
            if lat:
                print(f"  ✓ {item.get('address', '')[:60]}")
            else:
                print(f"  ✗ {item.get('address', '')[:60]}")

    # Export only active listings to data.json (frontend reads this)
    data = sorted(
        [v for v in existing.values() if v.get("is_active", True)],
        key=lambda x: x.get("price", 0),
    )

    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save full state (including inactive) for tracking stale listings across runs
    all_items = sorted(existing.values(), key=lambda x: x.get("url", ""))
    STATE_JSON.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")

    inactive = len(all_items) - len(data)
    print(f"\n✓ {len(data)} active listings ({new_count} new, {inactive} inactive) → {DATA_JSON}")


asyncio.run(main())
