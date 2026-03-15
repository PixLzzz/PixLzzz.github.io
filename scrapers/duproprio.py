"""DuProprio.com scraper — Plateau-Mont-Royal + Rosemont."""
import logging
import math
import re
from typing import Dict, List

import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# DuProprio neighbourhood pages
SEARCH_URLS = [
    ("https://duproprio.com/fr/montreal/le-plateau-mont-royal", "Plateau-Mont-Royal"),
    ("https://duproprio.com/fr/montreal/rosemont-la-petite-patrie", "Rosemont-La Petite-Patrie"),
]
ITEMS_PER_PAGE = 11


class DuProprioScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        results = []
        seen = set()
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
        }

        with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as c:
            for base_url, neighborhood in SEARCH_URLS:
                # Get page 1 to find total count
                r = c.get(base_url)
                soup = self._parse(r.text)
                total_el = soup.select_one(
                    ".search-results-listings-header__properties-found__number"
                )
                total = int(total_el.text.strip()) if total_el else 0
                logger.info(f"DuProprio: {total} total listings in {neighborhood}")
                num_pages = math.ceil(total / ITEMS_PER_PAGE) if total else 1

                for page in range(1, num_pages + 1):
                    url = base_url if page == 1 else f"{base_url}?pageNumber={page}"
                    try:
                        r = c.get(url)
                        soup = self._parse(r.text)
                        items = self._extract(soup, neighborhood)
                        logger.info(f"DuProprio {neighborhood} page {page}: {len(items)} items")
                        for item in items:
                            if item["url"] not in seen:
                                seen.add(item["url"])
                                results.append(item)
                    except Exception as e:
                        logger.error(f"DuProprio page {page} error: {e}")

        logger.info(f"DuProprio: returning {len(results)} listings")
        return results

    def _parse(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _extract(self, soup: BeautifulSoup, neighborhood: str = "Plateau-Mont-Royal") -> List[Dict]:
        items = []
        lis = soup.select("li.search-results-listings-list__item")
        for li in lis:
            bottom = li.select_one(".search-results-listings-list__item-bottom-container")
            if not bottom:
                continue

            url = bottom.get("href", "")
            if not url:
                continue

            price_el = bottom.select_one(
                ".search-results-listings-list__item-description__price h2"
            )
            city_el = bottom.select_one(
                ".search-results-listings-list__item-description__city"
            )
            addr_el = bottom.select_one(
                ".search-results-listings-list__item-description__address"
            )
            img_el = li.select_one("img.search-results-listings-list__item-photo")

            # Bedrooms & bathrooms from characteristics items
            char_items = bottom.select(
                ".search-results-listings-list__item-description__characteristics__item"
            )
            bedrooms = bathrooms = 0
            area_sqft = 0.0
            for ch in char_items:
                svg = ch.select_one("svg")
                text = ch.get_text(strip=True)
                if svg:
                    cls = " ".join(svg.get("class", []))
                    if "bedrooms" in cls:
                        bedrooms = self._parse_int(text)
                    elif "bathrooms" in cls:
                        bathrooms = self._parse_int(text)
                if "pi²" in text or "sqft" in text.lower():
                    area_sqft = self._parse_area(text)

            city = city_el.get_text(strip=True) if city_el else ""
            address = addr_el.get_text(strip=True) if addr_el else ""
            full_address = f"{address}, {city}".strip(", ")

            desc_el = bottom.select_one(
                ".search-results-listings-list__item-description__type-and-intro"
            )
            description = desc_el.get_text(strip=True) if desc_el else ""
            full_text = li.get_text(" ", strip=True)
            has_terrace = bool(
                re.search(r"terrasse|terrace", full_text, re.IGNORECASE)
            )

            items.append({
                "source": "duproprio",
                "url": url,
                "title": "",
                "price": self._parse_price(price_el.get_text() if price_el else ""),
                "address": full_address,
                "neighborhood": neighborhood,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "area_sqft": area_sqft,
                "image_url": img_el.get("src", "") if img_el else "",
                "description": description,
                "has_terrace": has_terrace,
            })

        return items
