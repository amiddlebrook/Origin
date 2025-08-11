import asyncio
import logging
from celery_app import celery
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models_story import NameStory
from app.models import Research
from app.services.story_builder import compose_story_from_results
from app.services.scraping.etymonline_scraper import EtymonlineScraper
from app.services.scraping.wikipedia_scraper import WikipediaScraper
from app.services.scraping.behindthename_scraper import BehindTheNameScraper

logger = logging.getLogger(__name__)


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _gather_results(seed_name: str) -> dict:
    results = {}
    async with EtymonlineScraper() as et:
        results["etymonline"] = await et.search_name(seed_name)
    async with WikipediaScraper() as wp:
        results["wikipedia"] = await wp.search_name(seed_name)
    async with BehindTheNameScraper() as btn:
        results["behindthename"] = await btn.search_name(seed_name)
    return results


@celery.task(name="tasks.story_tasks.generate_name_story")
def generate_name_story(story_id: int, seed_name: str | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            # mark running
            async with db.begin():
                await db.execute(update(NameStory).where(NameStory.id == story_id).values(status="running"))

            # fetch story
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
                # scrape directly
                results = await _gather_results(seed_name)

            name = seed_name or "your name"
            narrative, sources = compose_story_from_results(name, results or {})

            async with db.begin():
                await db.execute(
                    update(NameStory)
                    .where(NameStory.id == story_id)
                    .values(narrative=narrative, sources=sources, status="done")
                )

    try:
        return run_async(_run())
    except Exception as e:
        logger.exception("Story generation failed for %s: %s", story_id, e)
        async def mark_error():
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await db.execute(update(NameStory).where(NameStory.id == story_id).values(status="error"))
        run_async(mark_error())
        raise
