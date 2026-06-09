import asyncio
import logging

import aiohttp

from core.dto import PostSchema
from core.scrapper.parser import parse_channel_posts
from core.exceptions import ChannelNotFound, ScrappingError


logger = logging.getLogger(__name__)


CHANNEL_URL_TEMPLATE = "https://t.me/s/{username}"
REQUEST_TIMEOUT = 30
FETCH_RETRIES = 3
FETCH_BACKOFF_BASE = 2.0  # seconds: 2, 4, 8 ...
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)


class ScrapperService:
    def __init__(self):
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def fetch_posts(
        self,
        username: str,
        limit: int = 20,
        order: str = "desc",
    ) -> list[PostSchema]:
        """Fetch and parse a channel's preview page in real time.

        No data is persisted: each call returns fresh posts with media URLs
        that are only seconds old, so the consumer can use them before the
        Telegram CDN links expire.
        """
        html = await self._fetch_channel_html(username)

        posts = await asyncio.to_thread(parse_channel_posts, html, username)
        if not posts:
            logger.info(f"[@{username}] Постов на странице не найдено")
            return []

        # parse_channel_posts already returns posts sorted by id desc.
        if order == "asc":
            posts = list(reversed(posts))

        if limit:
            posts = posts[:limit]

        logger.info(f"[@{username}] Отдаём {len(posts)} постов")
        return posts

    async def _fetch_channel_html(self, username: str) -> str:
        url = CHANNEL_URL_TEMPLATE.format(username=username)
        headers = {"User-Agent": USER_AGENT}

        last_error: Exception | None = None

        for attempt in range(1, FETCH_RETRIES + 1):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 404:
                            raise ChannelNotFound()
                        if response.status != 200:
                            raise ScrappingError(
                                f"[@{username}] HTTP {response.status}"
                            )
                        html = await response.text()

                logger.info(f"[@{username}] OK, {len(html) // 1024} KB")
                return html

            except ChannelNotFound:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < FETCH_RETRIES:
                    backoff = FETCH_BACKOFF_BASE ** attempt
                    logger.warning(
                        f"[@{username}] Ошибка загрузки "
                        f"({attempt}/{FETCH_RETRIES}): {e}. "
                        f"Повтор через {backoff:.0f}с"
                    )
                    await asyncio.sleep(backoff)

        raise ScrappingError(
            f"[@{username}] Не удалось загрузить страницу: {last_error}"
        )
