"""RE/MAX Quebec scraper — uses api.remax-quebec.com REST API."""
import logging
import re
from typing import Dict, List

import httpx

from config import CRITERIA
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

API_BASE = "https://api.remax-quebec.com/api/inscriptions/search"
API_KEY = "c4dWcBkE#RL78Y@zg4Y06M$qrOJAeh7Fwv!Z9T4Q1f@zZ"
PHOTO_BASE = "https://media.remax-quebec.com/img/www_small/"
LISTING_BASE = "https://www.remax-quebec.com/fr/proprietes/"

# Municipality keys from api.remax-quebec.com/api/data/geography
MUNICIPALITIES = [
    ("66508", "Plateau-Mont-Royal"),
    ("66511", "Rosemont-La Petite-Patrie"),
]

PAGE_SIZE = 50


class RemaxScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        results = []
        seen = set()
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
            "content-language": "fr",
            "Referer": "https://www.remax-quebec.com/",
            "x-header-api": API_KEY,
        }

        with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as c:
            for muni_key, neighborhood in MUNICIPALITIES:
                page = 1
                while True:
                    params = {
                        "ForSale": "true",
                        "OrderBy": "Date",
                        "OrderDir": "Desc",
                        "PageSize": str(PAGE_SIZE),
                        "page": str(page),
                        "PriceMin": str(CRITERIA["min_price"]),
                        "PriceMax": str(CRITERIA["max_price"]),
                        "Bedroom": str(CRITERIA["min_bedrooms"]),
                        "Municipalites[0]": muni_key,
                    }
                    try:
                        r = c.get(API_BASE, params=params)
                        data = r.json()
                        items = data.get("data", [])
                        meta = data.get("meta", {})
                        total = meta.get("total", 0)
                        last_page = meta.get("last_page", 1)

                        logger.info(
                            f"RE/MAX {neighborhood} page {page}/{last_page}: "
                            f"{len(items)} items (total {total})"
                        )

                        for item in items:
                            listing = self._parse_item(item, neighborhood)
                            if listing and listing["url"] not in seen:
                                seen.add(listing["url"])
                                results.append(listing)

                        if page >= last_page:
                            break
                        page += 1

                    except Exception as e:
                        logger.error(f"RE/MAX {neighborhood} page {page} error: {e}")
                        break

        logger.info(f"RE/MAX: returning {len(results)} listings")
        return results

    def _parse_item(self, item: dict, neighborhood: str) -> Dict | None:
        slug = (item.get("slug") or {}).get("fr", "")
        if not slug:
            return None

        url = LISTING_BASE + slug

        address_data = item.get("address") or {}
        address = (address_data.get("display") or {}).get("fr", "")

        photos = item.get("photos") or []
        image_url = ""
        if photos:
            image_url = PHOTO_BASE + photos[0].get("url", "")

        area_str = (item.get("superficie_habitable") or {}).get("fr", "")
        kind = (item.get("property_kind") or {}).get("fr", "")

        full_text = f"{kind} {address}"
        has_terrace = bool(re.search(r"terrasse|terrace|balcon", full_text, re.IGNORECASE))

        lat = address_data.get("latitude")
        lng = address_data.get("longitude")

        return {
            "source": "remax",
            "url": url,
            "title": kind,
            "price": float(item.get("price_sale", 0) or 0),
            "address": address,
            "neighborhood": neighborhood,
            "bedrooms": int(item.get("nb_of_bedrooms", 0) or 0),
            "bathrooms": int(item.get("nb_of_bathrooms", 0) or 0),
            "area_sqft": self._parse_area(area_str),
            "image_url": image_url,
            "description": "",
            "has_terrace": has_terrace,
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
        }
