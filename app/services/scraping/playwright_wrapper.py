import asyncio
import logging
logger = logging.getLogger(__name__)
async def render_page(url: str, timeout: int = 15):
    # optional import to avoid heavy dependency if not installed
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        logger.warning("Playwright not installed: %s", e)
        return None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=timeout*1000)
            await asyncio.sleep(1)  # let JS settle
            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        logger.exception("Playwright render failed: %s", e)
        return None
