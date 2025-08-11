from .base_scraper import BaseScraper
from typing import Dict, Any
from urllib.parse import quote_plus

class WikipediaScraper(BaseScraper):
    async def search_name(self, name: str) -> Dict[str, Any]:
        url = f"https://en.wikipedia.org/wiki/{quote_plus(name)}"
        soup = await self.fetch_page(url)
        out = {"url": url, "found": False, "intro": None}
        if not soup:
            return out
        # check for disambiguation or real page
        first_p = soup.select_one('p')
        if first_p:
            out['found'] = True
            out['intro'] = first_p.get_text(separator=' ', strip=True)[:1000]
        return out
