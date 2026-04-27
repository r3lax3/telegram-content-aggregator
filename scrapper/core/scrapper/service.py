import asyncio
import logging

import aiohttp

from core.scrapper.parser import parse_channel_posts
from core.database.uow import UnitOfWork
from core.exceptions import ChannelNotFound, ScrappingError


logger = logging.getLogger(__name__)


CHANNEL_URL_TEMPLATE = "https://t.me/s/{username}"
REQUEST_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)


class ScrapperService:
    def __init__(self):
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def update_data(self, uow: UnitOfWork, username: str) -> None:
        html = await self._fetch_channel_html(username)

        posts = await asyncio.to_thread(parse_channel_posts, html, username)
        if not posts:
            logger.info(f"[@{username}] Постов на странице не найдено")
            return

        await self._save_new_posts(uow, username, posts)

    async def _fetch_channel_html(self, username: str) -> str:
        url = CHANNEL_URL_TEMPLATE.format(username=username)
        headers = {"User-Agent": USER_AGENT}

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

    async def _save_new_posts(self, uow: UnitOfWork, username: str, posts) -> None:
        last_post = await uow.channels.get_last_post(username)
        last_id = last_post.id if last_post else 0

        new_posts = [p for p in posts if p.id > last_id]
        if not new_posts:
            logger.info(
                f"[@{username}] Новых постов нет "
                f"(всего на странице: {len(posts)}, last_id: {last_id})"
            )
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
