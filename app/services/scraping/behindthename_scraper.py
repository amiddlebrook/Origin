from .base_scraper import BaseScraper
from typing import Dict, Any
from urllib.parse import quote_plus

class BehindTheNameScraper(BaseScraper):
    async def search_name(self, name: str) -> Dict[str, Any]:
        # behindthename uses lowercase name in URL
        url = f"https://www.behindthename.com/name/{quote_plus(name.lower())}"
        soup = await self.fetch_page(url)
        out = {"url": url, "found": False, "meaning": None}
        if not soup:
            return out
        # Try to find meaning content
        m = soup.select_one('.namedata') or soup.select_one('.names') or soup.select_one('.browsename')
        if m:
            out['found'] = True
            out['meaning'] = m.get_text(separator=' ', strip=True)[:1200]
        return out
