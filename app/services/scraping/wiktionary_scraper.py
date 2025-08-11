from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from urllib.parse import quote_plus

class WiktionaryScraper(BaseScraper):
    async def search_name(self, name: str) -> Optional[Dict[str, Any]]:
        url = f"https://en.wiktionary.org/wiki/{quote_plus(name)}"
        soup: BeautifulSoup | None = await self.fetch_page(url)
        if not soup:
            return None
        # Try to get the first etymology section
        ety = soup.select_one("#Etymology") or soup.find(id=lambda x: x and x.lower().startswith("etymology"))
        text = None
        if ety:
            # capture following paragraph(s)
            p = ety.find_next("p")
            if p:
                text = p.get_text(" ", strip=True)
        if not text:
            # fallback: first paragraph on page
            p = soup.select_one("p")
            text = p.get_text(" ", strip=True) if p else None
        return {"url": url, "summary": text}
