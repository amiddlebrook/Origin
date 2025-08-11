from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from urllib.parse import quote_plus

class SurnameDBScraper(BaseScraper):
    async def search_name(self, surname: str) -> Optional[Dict[str, Any]]:
        # SurnameDB entries are typically at /surname/{name}
        url = f"https://www.surnamedb.com/Surname/{quote_plus(surname.capitalize())}"
        soup: BeautifulSoup | None = await self.fetch_page(url)
        if not soup:
            return None
        # Extract main article text
        main = soup.select_one(".content, .content-inner, article, #content") or soup
        paras = main.select("p") if main else []
        text = None
        for p in paras:
            t = p.get_text(" ", strip=True)
            if t and len(t) > 120:
                text = t
                break
        return {"url": url, "summary": text}
