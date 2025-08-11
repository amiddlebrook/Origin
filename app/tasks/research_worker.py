import logging
import asyncio
from urllib.parse import quote_plus
from app.services.scraping.base_scraper import BaseScraper
from app.database import AsyncSessionLocal
from sqlalchemy import select, update
from app.models import Research

logger = logging.getLogger(__name__)

async def process_research_job(db_session, research_id: int, name: str):
    await update_status(db_session, research_id, "running")

    results = {}
    try:
        async with BaseScraper() as s:
            ety_url = f"https://www.etymonline.com/search?q={quote_plus(name)}"
            soup = await s.fetch_page(ety_url)
            if soup:
                first = soup.select_one(".word--C9UPa") or soup.select_one(".search-result")
                results["etymonline_snippet"] = first.get_text(separator=" ", strip=True)[:200] if first else None
            else:
                results["etymonline_snippet"] = None

            wiki_url = f"https://en.wikipedia.org/wiki/{quote_plus(name)}"
            wsoup = await s.fetch_page(wiki_url)
            if wsoup:
                p = wsoup.select_one("p")
                results["wikipedia_intro"] = p.get_text(separator=" ", strip=True)[:400] if p else None
            else:
                results["wikipedia_intro"] = None

            btn_url = f"https://www.behindthename.com/name/{quote_plus(name.lower())}"
            b = await s.fetch_page(btn_url)
            if b:
                desc = b.select_one(".names")
                results["behindthename_snippet"] = desc.get_text(separator=" ", strip=True)[:300] if desc else None
            else:
                results["behindthename_snippet"] = None

        await save_result(db_session, research_id, results)
        await update_status(db_session, research_id, "done")
    except Exception as e:
        logger.exception("Error processing research job %s: %s", research_id, e)
        await save_error(db_session, research_id, str(e))
        await update_status(db_session, research_id, "error")

async def save_result(db_session, research_id: int, result: dict):
    async with db_session.begin():
        await db_session.execute(
            update(Research)
            .where(Research.id == research_id)
            .values(result=result, error=None)
        )

async def save_error(db_session, research_id: int, error_text: str):
    async with db_session.begin():
        await db_session.execute(
            update(Research)
            .where(Research.id == research_id)
            .values(error=error_text)
        )

async def update_status(db_session, research_id: int, status: str):
    async with db_session.begin():
        await db_session.execute(
            update(Research)
            .where(Research.id == research_id)
            .values(status=status)
        )

async def run_process_in_background(research_id: int, name: str):
    async with AsyncSessionLocal() as db:
        await process_research_job(db, research_id, name)
