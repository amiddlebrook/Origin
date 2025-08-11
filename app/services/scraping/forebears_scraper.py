from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from urllib.parse import quote_plus

class ForebearsScraper(BaseScraper):
    async def search_name(self, surname: str) -> Optional[Dict[str, Any]]:
        url = f"https://forebears.io/surnames/{quote_plus(surname.lower())}"
        soup: BeautifulSoup | None = await self.fetch_page(url)
        if not soup:
            return None
        # Extract a short summary and possible top countries table snippet
        summary = None
        lead = soup.select_one(".lead, .page-header + p, .content p")
        if lead:
            summary = lead.get_text(" ", strip=True)
        top = []
        table = soup.find("table")
        if table:
            for row in table.select("tr")[:6]:
                cells = [c.get_text(" ", strip=True) for c in row.select("th,td")]
                if len(cells) >= 2:
                    top.append(cells[:3])
        return {"url": url, "summary": summary, "top_rows": top}
