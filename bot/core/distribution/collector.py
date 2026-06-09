import asyncio
import logging

import aiohttp
from pydantic import ValidationError

from core.schemas.post import PostSchema


logger = logging.getLogger(__name__)


FETCH_RETRIES = 3
FETCH_BACKOFF_BASE = 2.0  # seconds: 2, 4, 8 ...
FETCH_TIMEOUT = 30


async def collect_posts_for_channel(
    scrapper_api_url: str,
    donor_usernames: list[str],
) -> list[PostSchema]:
    posts = []

    for username in donor_usernames:
        try:
            fetched = await fetch_latest_posts(scrapper_api_url, username)
        except Exception as e:
            logger.error(f"Ошибка при получении постов от @{username}: {e}")
            continue

        if fetched:
            logger.info(f"@{username}: получено {len(fetched)} постов")
            posts.extend(fetched)

    posts = sorted(
        posts,
        key=lambda post: post.created_at,
        reverse=True
    )

    return posts


async def fetch_latest_posts(
    scrapper_api_url: str,
    donor_channel: str,
) -> list[PostSchema]:
    """Fetch fresh posts for a donor channel, retrying transient failures.

    The scrapper serves these in real time, so a brief retry on a timeout keeps
    the media URLs fresh while giving the request a second chance to land.
    """
    last_error: Exception | None = None

    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            return await _request_posts(scrapper_api_url, donor_channel)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < FETCH_RETRIES:
                backoff = FETCH_BACKOFF_BASE ** attempt
                logger.warning(
                    f"@{donor_channel}: ошибка запроса к скрапперу "
                    f"({attempt}/{FETCH_RETRIES}): {e}. Повтор через {backoff:.0f}с"
                )
                await asyncio.sleep(backoff)

    raise RuntimeError(
        f"Не удалось получить посты @{donor_channel} от скраппера: {last_error}"
    )


async def _request_posts(
    scrapper_api_url: str,
    donor_channel: str,
) -> list[PostSchema]:
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{scrapper_api_url}/posts",
            params={
                "channel": donor_channel,
                "limit": 20,
                "order": "desc",
            },
            timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
        )
        response.raise_for_status()
        data = await response.json()

    if not isinstance(data, list):
        raise ValueError("Expected a list of posts from API")

    try:
        return [PostSchema.model_validate(item) for item in data]
    except ValidationError as e:
        raise ValueError(f"Invalid post data structure: {e}") from e
