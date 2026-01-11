import json
import asyncio
from asyncio import Event, TimeoutError
from pathlib import Path

from telethon import TelegramClient, events
from telethon.types import Message
from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth

from core.exceptions import ScrappingError
from core.logger import get_logger
from .telegram import get_telegram_client
from .utils import get_browser, get_context


logger = get_logger(__name__)

COOKIES_FILE = Path("cookies.json")


def load_cookies() -> list[dict]:
    if not COOKIES_FILE.exists():
        return []
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cookies(cookies: list[dict]) -> None:
    logger.info("Saving cookies to file...")
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)


async def update_cookies() -> None:
    logger.info("Starting cookie update procedure...")
    async with Stealth().use_async(async_playwright()) as p:
        browser = await get_browser(p)
        context = await get_context(browser)

        page = await context.new_page()
        try:
            logger.info("Opening TGStat homepage...")
            await _get_to_tgstat_homepage(page)

            logger.info("Getting TGStat auth code...")
            auth_code = await _get_auth_code(page)

            telegram_client = get_telegram_client()
            logger.info("Got Telegram client")

            async with telegram_client:
                authorized_event = asyncio.Event()
                _setup_tgstat_bot_message_handler(telegram_client, authorized_event)

                logger.info("Sending auth command to @tg_analytics_bot...")
                await telegram_client.send_message(
                    "tg_analytics_bot",
                    f"/start {auth_code}"
                )

                try:
                    logger.info("Waiting for bot authorization response...")
                    await asyncio.wait_for(authorized_event.wait(), timeout=15)
                except TimeoutError:
                    logger.error("Bot did not respond to auth request (timeout)!")
                    raise ScrappingError(
                        "Telegram bot @tg_analytics_bot is not responding."
                    )

                # Wait for browser to receive the auth event
                await asyncio.sleep(5)

                logger.info("Getting and saving browser cookies...")
                cookies = await context.cookies()
                save_cookies(cookies)

        except Exception:
            with open("live.html", "w", encoding="utf-8") as f:
                html = await page.content()
                f.write(html)
            raise

        finally:
            await context.close()
            await browser.close()

    logger.info("Cookie update procedure completed successfully.")


async def _get_auth_code(page: Page) -> str:
    await page.click("a:has-text('Вход на сайт')")
    await page.wait_for_selector("a.auth-btn")

    telegram_auth_button = await page.query_selector("a.auth-btn")
    auth_code = await telegram_auth_button.get_attribute("data-telegram-auth-button")
    logger.info(f"Auth code: {auth_code}")

    await telegram_auth_button.click()
    await asyncio.sleep(5)

    context = page.context
    # context.pages[0] — old tab, context.pages[1] — new tab
    if len(context.pages) == 2:
        new_page = context.pages[1]
    else:
        raise Exception(
            f"Expected two tabs (tgstat and new), got: {len(context.pages)}"
        )

    await new_page.close()
    logger.info("Opened and closed TG redirect, all ok")
    return auth_code


async def _get_to_tgstat_homepage(page: Page) -> None:
    url = "https://tgstat.ru"

    try:
        logger.info(f"Navigating to {url}...")
        await page.goto(url, timeout=40_000, wait_until="domcontentloaded")

        # Wait for login button (means page is loaded)
        await page.wait_for_selector("a:has-text('Вход на сайт')", timeout=30_000)
        logger.info("TGStat page loaded successfully.")

    except TimeoutError:
        html = await page.content()
        with open("auth_error.html", "w", encoding="utf-8") as f:
            f.write(html)

        logger.error(
            "TimeoutError while waiting for https://tgstat.ru/ response. "
            "HTML saved to auth_error.html"
        )
        raise ScrappingError()


def _setup_tgstat_bot_message_handler(
    telegram_client: TelegramClient,
    authorized_event: Event,
) -> None:
    @telegram_client.on(events.NewMessage(from_users="tg_analytics_bot"))
    async def handler(event: Message):
        logger.info("Received message from @tg_analytics_bot...")
        if "Вы входите на сайт" not in event.text:
            return

        await event.click(0)
        logger.info("Clicked 'Authorize'.")
        authorized_event.set()
        telegram_client.disconnect()
