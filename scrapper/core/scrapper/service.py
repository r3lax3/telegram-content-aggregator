import json
import logging
import asyncio
from pathlib import Path

from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeoutError
from telethon import TelegramClient, events

from core.scrapper.browser import PlaywrightManager
from core.scrapper.parser import parse_channel_posts
from core.database.uow import UnitOfWork
from core.exceptions import (
    ChannelNotFound,
    ScrappingError,
    RobotSuspicion,
    TelegramSessionNotFound,
)


logger = logging.getLogger(__name__)


COOKIES_PATH = Path("cookies.json")
TG_SESSION_PATH = Path("tg_acc.session")
TG_API_ID = 37443963
TG_API_HASH = "f5092f2f7523d78fb82fbe6ff126bb60"


class ScrapperService:
    def __init__(self, pw_manager: PlaywrightManager):
        self._pw_manager = pw_manager
        self._validate_telegram_session()

    def _validate_telegram_session(self):
        if not TG_SESSION_PATH.exists():
            raise TelegramSessionNotFound(
                f"Telegram session not found at {TG_SESSION_PATH}. "
                "Run `python scripts/create_tg_session.py` first."
            )

    @property
    def _context(self) -> BrowserContext:
        return self._pw_manager.context

    async def update_data(self, uow: UnitOfWork, username: str) -> None:
        """Главный метод — загружает и сохраняет новые посты канала."""
        html = await self._fetch_channel_html(username)

        posts = parse_channel_posts(html, username)
        if not posts:
            logger.info(f"[@{username}] Постов на странице не найдено")
            return

        await self._save_new_posts(uow, username, posts)

    async def _fetch_channel_html(self, username: str) -> str:
        """Загружает HTML страницы канала, при необходимости обновляет куки."""
        for attempt in range(2):
            cookies = self._load_cookies()
            if not cookies:
                await self._regenerate_cookies()
                cookies = self._load_cookies()

            try:
                return await self._try_fetch(username, cookies)
            except RobotSuspicion:
                logger.info(f"429 при загрузке @{username}, ждём 60 сек...")
                await asyncio.sleep(60)
            except PlaywrightTimeoutError:
                logger.info(f"Timeout при загрузке @{username}, ждём 60 сек...")
                await asyncio.sleep(60)

        raise ScrappingError(f"Не удалось загрузить канал @{username}")

    async def _try_fetch(self, username: str, cookies: list[dict]) -> str:
        """Одна попытка загрузки HTML."""
        await self._context.add_cookies(cookies)
        page = await self._context.new_page()

        try:
            url = f"https://tgstat.ru/channel/@{username}"
            response = await page.goto(url, wait_until="domcontentloaded", timeout=40_000)

            if response.status == 404:
                raise ChannelNotFound()

            if not response or response.status != 200:
                logger.info(f"[@{username}] HTTP {response.status if response else 'None'}")
                raise ScrappingError()

            await page.wait_for_timeout(30_000)

            title = await page.title()
            if "just a moment" in title.lower() or "checking your browser" in title.lower():
                logger.info(f"[@{username}] Cloudflare challenge")
                raise ScrappingError()

            if "429" in title:
                raise RobotSuspicion()

            html = await page.content()
            logger.info(f"[@{username}] OK, {len(html) // 1024} KB")
            return html

        finally:
            await page.close()

    async def _save_new_posts(self, uow: UnitOfWork, username: str, posts) -> None:
        """Фильтрует и сохраняет только новые посты."""
        last_post = await uow.channels.get_last_post(username)
        last_id = last_post.id if last_post else 0

        new_posts = [p for p in posts if p.id > last_id]
        if not new_posts:
            logger.info(f"[@{username}] Новых постов нет (всего на странице: {len(posts)}, last_id: {last_id})")
            return

        for post_dto in new_posts:
            await uow.posts.add(
                id=post_dto.id,
                channel_username=post_dto.channel_username,
                text=post_dto.text,
                created_at=post_dto.created_at,
            )
            for media in post_dto.medias:
                await uow.media.add(
                    post_id=post_dto.id,
                    post_channel_username=post_dto.channel_username,
                    type=media.type,
                    url=media.url,
                )

        logger.info(f"[@{username}] Сохранено {len(new_posts)} новых постов")

    def _load_cookies(self) -> list[dict]:
        if not COOKIES_PATH.exists():
            return []

        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_cookies(self, cookies: list[dict]) -> None:
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

    async def _regenerate_cookies(self) -> None:
        """Авторизация на tgstat.ru через Telegram бота."""
        logger.info("Обновление cookies через Telegram...")

        page = await self._context.new_page()
        try:
            await page.goto("https://tgstat.ru", timeout=40_000, wait_until="domcontentloaded")
            await page.wait_for_selector("a:has-text('Вход на сайт')", timeout=30_000)

            await page.click("a:has-text('Вход на сайт')")
            await page.wait_for_selector("a.auth-btn")

            auth_btn = await page.query_selector("a.auth-btn")
            auth_code = await auth_btn.get_attribute("data-telegram-auth-button")
            logger.info(f"Код авторизации: {auth_code}")

            await auth_btn.click()
            await asyncio.sleep(3)

            # закрываем новую вкладку если открылась
            if len(self._context.pages) > 1:
                await self._context.pages[-1].close()

            await self._authorize_via_telegram(auth_code)
            await asyncio.sleep(5)

            cookies = await self._context.cookies()
            self._save_cookies(cookies)
            logger.info("Cookies успешно обновлены")

        finally:
            await page.close()

    async def _authorize_via_telegram(self, auth_code: str) -> None:
        """Отправляет код боту и нажимает кнопку авторизации."""
        client = TelegramClient("tg_acc", TG_API_ID, TG_API_HASH)
        authorized = asyncio.Event()

        @client.on(events.NewMessage(from_users="tg_analytics_bot"))
        async def handler(event):
            if "Вы входите на сайт" in event.text:
                await event.click(0)
                logger.info("Нажали 'Авторизоваться' в Telegram")
                authorized.set()

        async with client:
            await client.send_message("tg_analytics_bot", f"/start {auth_code}")
            try:
                await asyncio.wait_for(authorized.wait(), timeout=15)
            except asyncio.TimeoutError:
                raise ScrappingError("Telegram бот не ответил на запрос авторизации")
