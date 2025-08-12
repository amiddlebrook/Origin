import asyncio
import time
import logging
import random
import re
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
from app.core.config import settings
try:
    from fake_useragent import UserAgent
except Exception:
    UserAgent = None
logger = logging.getLogger(__name__)

class DomainRateLimiter:
    def __init__(self, delay: float):
        self.delay = delay
        self.lock = asyncio.Lock()
        self._last = 0.0
    async def wait(self):
        async with self.lock:
            now = time.time()
            wait_for = max(0, self._last + self.delay - now)
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last = time.time()

class BaseScraper:
    def __init__(self, session: Optional[aiohttp.ClientSession]=None, retries: int=3, backoff_factor: float=0.5):
        self._external_session = session
        self.session = session
        self.retries = retries
        self.backoff = backoff_factor
        self.ua = self._init_ua()
        self.rate_limiters = {}
        self.default_delay = settings.REQUEST_DELAY
        self.sem = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self.playwright_enabled = settings.ENABLE_PLAYWRIGHT

    def _init_ua(self):
        if UserAgent:
            try:
                return UserAgent().random
            except Exception:
                pass
        # fallback list
        fallbacks = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        ]
        return random.choice(fallbacks)

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _ensure_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": self.ua, "Accept-Language":"en-US,en;q=0.9"}
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def close(self):
        if self.session and not self._external_session:
            try:
                await self.session.close()
            finally:
                self.session = None

    def _get_limiter(self, domain: str):
        if domain not in self.rate_limiters:
            self.rate_limiters[domain] = DomainRateLimiter(self.default_delay)
        return self.rate_limiters[domain]

    def _is_captcha(self, text: str) -> bool:
        if not text:
            return False
        patterns = [r"captcha", r"are you human", r"please enable javascript", r"cf-chl", r"recaptcha"]
        t = text.lower()
        return any(p in t for p in patterns)

    async def _fetch(self, url: str, method: str="GET", **kwargs):
        domain = re.sub(r'^https?://', '', url).split('/')[0]
        limiter = self._get_limiter(domain)
        await limiter.wait()
        attempt = 0
        while attempt < self.retries:
            attempt += 1
            try:
                async with self.sem:
                    start = time.time()
                    # rotate UA occasionally
                    if UserAgent and attempt > 1:
                        try:
                            hdr = {"User-Agent": UserAgent().random}
                            if self.session and hasattr(self.session, 'headers'):
                                self.session.headers.update(hdr)
                        except Exception:
                            pass
                    async with self.session.request(method, url, **kwargs) as resp:
                        text = await resp.text(errors='ignore')
                        duration = time.time() - start
                        if resp.status >= 500:
                            logger.warning("Server error %s on %s (attempt %s)", resp.status, url, attempt)
                            raise aiohttp.ClientResponseError(status=resp.status, request_info=resp.request_info, history=resp.history)
                        # detect captcha
                        if self._is_captcha(text):
                            logger.warning("Captcha detected on %s", url)
                            return {"status":"captcha", "status_code": resp.status, "text": text}
                        return {"status":"ok", "status_code": resp.status, "text": text, "duration": duration}
            except Exception as e:
                backoff = self.backoff * (2 ** (attempt - 1))
                logger.debug("Fetch error %s on %s attempt %s, backoff %s", e, url, attempt, backoff)
                await asyncio.sleep(backoff)
                last_exc = e
        # after retries
        logger.exception("Failed to fetch %s after %s attempts", url, self.retries)
        return {"status":"error", "error": str(last_exc)}

    async def fetch_page(self, url: str, method: str="GET", **kwargs):
        await self._ensure_session()
        res = await self._fetch(url, method, **kwargs)
        if not res or res.get("status") != "ok":
            # optional playwright fallback
            if self.playwright_enabled:
                try:
                    from app.services.scraping.playwright_wrapper import render_page
                    logger.info("Using Playwright fallback for %s", url)
                    html = await render_page(url)
                    if html:
                        return BeautifulSoup(html, "lxml")
                except Exception as e:
                    logger.exception("Playwright fallback failed for %s: %s", url, e)
            return None
        return BeautifulSoup(res.get("text",""), "lxml")

    async def fetch_json(self, url: str, **kwargs):
        await self._ensure_session()
        res = await self._fetch(url, **kwargs)
        if res and res.get("status") == "ok":
            try:
                import json
                return json.loads(res.get("text",""))
            except Exception:
                return None
        return None
