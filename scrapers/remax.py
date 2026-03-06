"""
RE/MAX Quebec scraper.

NOTE: In Quebec, all real estate brokers (including RE/MAX) are legally
required by the OACIQ to list properties on Centris.ca. RE/MAX Quebec
listings are therefore already included in the Centris scraper results.

This scraper is kept as a placeholder. It returns an empty list and logs
a note explaining the situation. The Centris scraper effectively covers
all RE/MAX listings in the Montreal area.
"""
import logging
from typing import Dict, List

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RemaxScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        logger.info(
            "RE/MAX Quebec: all listings are on Centris.ca by OACIQ regulation. "
            "No separate scrape needed — Centris already includes RE/MAX listings."
        )
        return []
