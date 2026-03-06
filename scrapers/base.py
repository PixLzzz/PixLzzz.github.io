"""Base scraper with shared utilities."""
import os
import re
import socket
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

# Inject extracted system libs so Playwright's Chromium can find libnss3 etc.
_LIB_PATH = str(Path.home() / "lib_extract" / "usr" / "lib" / "x86_64-linux-gnu")
if Path(_LIB_PATH).exists():
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    if _LIB_PATH not in existing:
        os.environ["LD_LIBRARY_PATH"] = f"{_LIB_PATH}:{existing}" if existing else _LIB_PATH


def build_dns_rules(*domains: str) -> str:
    """Pre-resolve domains and return a --host-resolver-rules string for Chromium."""
    rules = []
    for d in domains:
        try:
            ip = socket.gethostbyname(d)
            rules.append(f"MAP {d} {ip}")
        except OSError:
            pass
    return ",".join(rules)


BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
]

# Environment for the Chromium subprocess — needed so it finds extracted libnss3 etc.
BROWSER_ENV = {**os.environ, "LD_LIBRARY_PATH": _LIB_PATH}


class BaseScraper(ABC):
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        pass

    def _parse_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        digits = re.sub(r"[^\d.]", "", price_str)
        try:
            return float(digits) if digits else 0.0
        except ValueError:
            return 0.0

    def _parse_int(self, text: str) -> int:
        if not text:
            return 0
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 0

    def _parse_area(self, text: str) -> float:
        if not text:
            return 0.0
        clean = text.replace(",", "").replace(" ", "")
        match = re.search(r"([\d]+(?:\.\d+)?)", clean)
        try:
            return float(match.group(1)) if match else 0.0
        except ValueError:
            return 0.0
