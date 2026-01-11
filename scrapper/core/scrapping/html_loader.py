import asyncio

from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from core.exceptions import ChannelNotFound, ScrappingError, RobotSuspicion
from core.logger import get_logger
from .cookies import load_cookies, update_cookies
from .utils import get_browser, get_context, log_html


logger = get_logger(__name__)


async def get_channel_info_html(username: str) -> str:
    for attempt in range(2):
        cookies = load_cookies()
        if not cookies:
            await update_cookies()
            cookies = load_cookies()

        try:
            html = await _try_scrap_html(username, cookies)
            return html

        except (RobotSuspicion, PlaywrightTimeoutError):
            logger.warning(f"Attempt {attempt + 1} failed, waiting 60s before retry...")
            await asyncio.sleep(60)
            continue

    logger.error(
        f"Cannot update channel data https://tgstat.ru/channel/@{username}"
    )
    raise ScrappingError()


async def _try_scrap_html(username: str, cookies: list[dict]) -> str:
    target_url = f"https://tgstat.ru/channel/@{username}"

    async with Stealth().use_async(async_playwright()) as p:
        browser = await get_browser(p)
        context = await get_context(browser)

        await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            response = await page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=40_000
            )

            if response.status == 404:
                raise ChannelNotFound()

            if not response or response.status != 200:
                logger.info(
                    f"[{username}] HTTP {response.status if response else 'None'}"
                )
                if response:
                    html = await page.content()
                    log_html(html, f"data/error-{username}.html")

                raise ScrappingError()

            # Small buffer for potential redirects
            await page.wait_for_timeout(30000)

            title = await page.title()
            if "just a moment" in title.lower() or "checking your browser" in title.lower():
                logger.info(f"[{username}] Cloudflare caught us")
                html = await page.content()
                log_html(html, f"data/error-{username}.html")
                raise ScrappingError()

            if "429" in title:
                logger.info("Error 429 (Robot suspicion)")
                raise RobotSuspicion()

            html = await page.content()
            logger.info(
                f"[{username}] Success! {len(html) // 1024} KB, "
                f"status - {response.status}"
            )
            return html

        except ChannelNotFound:
            raise

        except PlaywrightTimeoutError:
            raise

        except Exception as e:
            logger.error(f"[{username}] ERROR: {e}", exc_info=True)
            raise

        finally:
            with open("debug.html", "w", encoding="utf-8") as f:
                html = await page.content()
                f.write(html)
            await context.close()
            await browser.close()
