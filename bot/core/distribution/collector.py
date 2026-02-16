import logging

import aiohttp
from pydantic import ValidationError

from core.schemas.post import PostSchema


logger = logging.getLogger(__name__)


async def collect_posts_for_channel(
    scrapper_api_url: str,
    donor_usernames: list[str],
) -> list[PostSchema]:
    posts = []

    for username in donor_usernames:
        fetched = await fetch_latest_posts(scrapper_api_url, username)
        if fetched:
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
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{scrapper_api_url}/posts",
            params={
                "channel": donor_channel,
                "limit": 20,
                "order": "desc",
                "unmarked": "true",
            },
            timeout=aiohttp.ClientTimeout(total=10)
        )
        response.raise_for_status()
        data = await response.json()

        if not isinstance(data, list):
            raise ValueError("Expected a list of posts from API")

        try:
            posts = [PostSchema.model_validate(item) for item in data]
            return posts

        except ValidationError as e:
            raise ValueError(f"Invalid post data structure: {e}") from e
