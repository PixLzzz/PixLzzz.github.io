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
from datetime import datetime, timezone
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
from scrapers.remax import RemaxScraper

DATA_JSON = ROOT / "frontend" / "public" / "data.json"


def clean_address(address: str) -> str:
    """Strip tabs, collapse whitespace, remove parenthesized city suffixes."""
    addr = re.sub(r"\t+", " ", address)           # tabs → space
    addr = re.sub(r"\s{2,}", " ", addr).strip()    # collapse whitespace
    addr = re.sub(r"\s*\(.*?\)\s*$", "", addr)     # remove trailing "(Le Plateau-Mont-Royal)"
    # Remove "apt." / "app." suffixes that confuse Nominatim
    addr = re.sub(r",?\s*(?:apt|app)\.?\s*\d+\w*", "", addr, flags=re.IGNORECASE)
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
    # Load existing snapshot keyed by URL
    existing: dict[str, dict] = {}
    if DATA_JSON.exists():
        try:
            for item in json.loads(DATA_JSON.read_text(encoding="utf-8")):
                existing[item["url"]] = item
            print(f"Loaded {len(existing)} existing listings from data.json")
        except Exception as e:
            print(f"Warning: could not read data.json: {e}")

    now = datetime.now(timezone.utc).isoformat()
    new_count = 0

    for name, scraper in [
        ("centris",   CentrisScraper()),
        ("duproprio", DuProprioScraper()),
        ("remax",     RemaxScraper()),
    ]:
        try:
            raw = await scraper.scrape()
            kept = [r for r in raw if matches_criteria(r)]
            print(f"{name}: {len(raw)} scraped, {len(kept)} match criteria")

            for item in kept:
                url = item["url"]
                if url in existing:
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

    # Retroactively geocode listings that have null coordinates
    missing_geo = [v for v in existing.values() if not v.get("latitude") or not v.get("longitude")]
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

    data = sorted(
        [v for v in existing.values() if v.get("is_active", True)],
        key=lambda x: x.get("price", 0),
    )

    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ {len(data)} listings ({new_count} new) → {DATA_JSON}")


asyncio.run(main())
