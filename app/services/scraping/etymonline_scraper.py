from .base_scraper import BaseScraper
from typing import Dict, Any
from urllib.parse import quote_plus

class EtymonlineScraper(BaseScraper):
    async def search_name(self, name: str) -> Dict[str, Any]:
        """Return structured result for Etymonline."""
        url = f"https://www.etymonline.com/search?q={quote_plus(name)}"
        soup = await self.fetch_page(url)
        out = {"url": url, "found": False, "snippet": None}
        if not soup:
            return out
        # attempt to find article title or first result
        first = soup.select_one('.word--C9UPa') or soup.select_one('.search-result') or soup.select_one('article')
        if first:
            out['found'] = True
            out['snippet'] = first.get_text(separator=' ', strip=True)[:800]
        return out
