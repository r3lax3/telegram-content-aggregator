import os

from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
from playwright_stealth import Stealth


class PlaywrightManager:
    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._stealth = Stealth()

    async def __aenter__(self) -> "PlaywrightManager":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-extensions",
                "--disable-default-apps",
                "--no-first-run",
                "--disable-translate",
                "--renderer-process-limit=1",
                "--disable-site-isolation-trials",
                "--disable-software-rasterizer",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-ipc-flooding-protection",
                "--disable-component-update",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            # TODO отвязать от ос и привязать к настройкам
            proxy={
                "server": os.getenv("PROXY_SERVER"),  # pyright: ignore
                "username": os.getenv("PROXY_USERNAME"), # pyright: ignore
                "password": os.getenv("PROXY_PASSWORD"), # pyright: ignore
            } if os.getenv("PROXY_SERVER") else None,
        )
        await self._stealth.apply_stealth_async(self._context)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for name, coro in [
            ("context", self._context.close() if self._context else None),
            ("browser", self._browser.close() if self._browser else None),
            ("playwright", self._playwright.stop() if self._playwright else None),
        ]:
            if coro is None:
                continue
            try:
                await coro
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error closing {name}: {e}")

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("PlaywrightManager not initialized")
        return self._context
