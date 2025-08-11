import logging
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models_story import NameStory
from app.models import Research
from app.services.story_builder import compose_story_from_results
from app.services.scraping.etymonline_scraper import EtymonlineScraper
from app.services.scraping.wikipedia_scraper import WikipediaScraper
from app.services.scraping.behindthename_scraper import BehindTheNameScraper
from app.services.scraping.wiktionary_scraper import WiktionaryScraper
from app.services.scraping.forebears_scraper import ForebearsScraper
from app.services.scraping.surnamedb_scraper import SurnameDBScraper

logger = logging.getLogger(__name__)


async def _gather_results(seed_name: str) -> dict:
    results = {}
    async with EtymonlineScraper() as et:
        results["etymonline"] = await et.search_name(seed_name)
    async with WikipediaScraper() as wp:
        results["wikipedia"] = await wp.search_name(seed_name)
    async with BehindTheNameScraper() as btn:
        results["behindthename"] = await btn.search_name(seed_name)
    async with WiktionaryScraper() as wt:
        results["wiktionary"] = await wt.search_name(seed_name)
    async with ForebearsScraper() as fb:
        results["forebears"] = await fb.search_name(seed_name)
    async with SurnameDBScraper() as sdb:
        results["surnamedb"] = await sdb.search_name(seed_name)
    return results


async def run_process_in_background(story_id: int, seed_name: str | None):
    async with AsyncSessionLocal() as db:
        # mark running
        async with db.begin():
            await db.execute(update(NameStory).where(NameStory.id == story_id).values(status="running"))

        res = await db.execute(select(NameStory).where(NameStory.id == story_id))
        story = res.scalar_one_or_none()
        if not story:
            return

        results = None
        if story.research_id:
            q = await db.execute(select(Research).where(Research.id == story.research_id))
            r = q.scalar_one_or_none()
            if r and r.result:
                results = r.result

        if results is None and seed_name:
            results = await _gather_results(seed_name)

        name = seed_name or "your name"
        narrative, sources = compose_story_from_results(name, results or {})

        async with db.begin():
            await db.execute(
                update(NameStory)
                .where(NameStory.id == story_id)
                .values(narrative=narrative, sources=sources, status="done")
            )
