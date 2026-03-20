"""Centris.ca scraper — Plateau-Mont-Royal / Mile-End / Rosemont."""
import logging
from typing import Dict, List

from playwright.async_api import async_playwright

from scrapers.base import BROWSER_ARGS, BROWSER_ENV, BaseScraper, build_dns_rules

logger = logging.getLogger(__name__)

SEARCH_URLS = [
    ("https://www.centris.ca/en/properties~for-sale~montreal-le-plateau-mont-royal", "Plateau-Mont-Royal"),
    ("https://www.centris.ca/en/properties~for-sale~montreal-rosemont-la-petite-patrie", "Rosemont-La Petite-Patrie"),
]

EXTRACT_JS = """() => {
    const items = document.querySelectorAll(".property-thumbnail-item");
    return Array.from(items).map(item => {
        const link = item.querySelector("a.property-thumbnail-summary-link");
        const price = item.querySelector(".price");
        const address = item.querySelector(".address");
        const category = item.querySelector(".category");
        const cac = item.querySelector(".cac");
        const sdb = item.querySelector(".sdb");
        const sqft = item.querySelector(".sqft") || item.querySelector("[class*=sqft]");
        const img = item.querySelector("img.img-responsive") || item.querySelector("img");
        const fullText = item.textContent || "";
        return {
            url: link ? "https://www.centris.ca" + link.getAttribute("href") : "",
            price: price ? price.textContent.trim() : "",
            address: address ? address.textContent.trim() : "",
            title: category ? category.textContent.trim() : "",
            bedrooms: cac ? cac.textContent.trim() : "",
            bathrooms: sdb ? sdb.textContent.trim() : "",
            area: sqft ? sqft.textContent.trim() : "",
            image_url: img ? img.src : "",
            has_terrace: /terrasse|terrace/i.test(fullText),
        };
    }).filter(x => x.url);
}"""


class CentrisScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        results = []
        seen = set()
        dns_rules = build_dns_rules("www.centris.ca", "centris.ca")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS + [f"--host-resolver-rules={dns_rules}"],
                env=BROWSER_ENV,
            )
            ctx = await browser.new_context(user_agent=self.USER_AGENT, locale="en-CA")
            page = await ctx.new_page()

            # Dismiss cookie consent once
            try:
                await page.goto(SEARCH_URLS[0][0], timeout=30_000)
                await page.wait_for_timeout(2000)
                await page.click("#didomi-notice-agree-button", timeout=5000)
                await page.wait_for_timeout(1000)
                logger.info("Centris: consent dismissed")
            except Exception as e:
                logger.warning(f"Centris: consent dismiss failed: {e}")

            for url, neighborhood in SEARCH_URLS:
                try:
                    logger.info(f"Centris: loading {url}")
                    await page.goto(url, timeout=30_000)

                    # Wait for listings
                    await page.wait_for_selector(".property-thumbnail-item", timeout=15_000)
                    await page.wait_for_timeout(1000)

                    # Paginate through all pages
                    page_num = 1
                    while True:
                        logger.info(f"Centris: extracting page {page_num}")
                        raw = await page.evaluate(EXTRACT_JS)

                        for item in raw:
                            listing_url = item.get("url", "")
                            if not listing_url or listing_url in seen:
                                continue
                            seen.add(listing_url)
                            results.append({
                                "source": "centris",
                                "url": listing_url,
                                "title": item.get("title", ""),
                                "price": self._parse_price(item.get("price", "")),
                                "address": item.get("address", "").replace("\n", " ").replace("\t", " ").strip(),
                                "neighborhood": neighborhood,
                                "bedrooms": self._parse_int(item.get("bedrooms", "")),
                                "bathrooms": self._parse_int(item.get("bathrooms", "")),
                                "area_sqft": self._parse_area(item.get("area", "")),
                                "image_url": item.get("image_url", ""),
                                "description": "",
                                "has_terrace": bool(item.get("has_terrace", False)),
                            })

                        # Try to go to next page
                        next_btn = await page.query_selector("li.next:not(.disabled) a, a[aria-label='Next']")
                        if not next_btn:
                            break
                        await next_btn.click()
                        await page.wait_for_selector(".property-thumbnail-item", timeout=10_000)
                        await page.wait_for_timeout(500)
                        page_num += 1
                        if page_num > 10:
                            break

                except Exception as e:
                    logger.error(f"Centris scrape error for {url}: {e}")

            await browser.close()

        logger.info(f"Centris: returning {len(results)} listings")
        return results
