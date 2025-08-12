import asyncio
import logging
from celery_app import celery
from app.services.scraping.etymonline_scraper import EtymonlineScraper
from app.services.scraping.wikipedia_scraper import WikipediaScraper
from app.services.scraping.behindthename_scraper import BehindTheNameScraper
from app.services.scraping.wiktionary_scraper import WiktionaryScraper
from app.services.scraping.forebears_scraper import ForebearsScraper
from app.services.scraping.surnamedb_scraper import SurnameDBScraper
from app.database import AsyncSessionLocal
from sqlalchemy import update
from app.models import Research

logger = logging.getLogger(__name__)

def run_async(coro):
    # helper for running async coroutines inside celery sync worker
    return asyncio.get_event_loop().run_until_complete(coro)

@celery.task(name='tasks.research_tasks.run_name_research')
def run_name_research(research_id: int, name: str):
    """Orchestrate scrapers and write results to DB."""
    async def _run():
        results = {}
        # instantiate scrapers
        async with EtymonlineScraper() as et:
            results['etymonline'] = await et.search_name(name)
        async with WikipediaScraper() as wp:
            results['wikipedia'] = await wp.search_name(name)
        async with BehindTheNameScraper() as btn:
            results['behindthename'] = await btn.search_name(name)
        async with WiktionaryScraper() as wt:
            results['wiktionary'] = await wt.search_name(name)
        # Surnames/distribution
        async with ForebearsScraper() as fb:
            results['forebears'] = await fb.search_name(name)
        async with SurnameDBScraper() as sdb:
            results['surnamedb'] = await sdb.search_name(name)

        # Save into DB
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await db.execute(
                    update(Research)
                    .where(Research.id == research_id)
                    .values(result=results, status='done', error=None)
                )

        return results

    try:
        # mark running
        async def mark_running():
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await db.execute(
                        update(Research)
                        .where(Research.id == research_id)
                        .values(status='running')
                    )
        run_async(mark_running())

        res = run_async(_run())
        return {"status": "ok", "result": res}
    except Exception as e:
        logger.exception("Celery task failed: %s", e)
        async def mark_error(exc: Exception):
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await db.execute(
                        update(Research)
                        .where(Research.id == research_id)
                        .values(status='error', error=str(exc))
                    )
        run_async(mark_error(e))
        raise
