from typing import List

from core.domain import UOW
from core.dto import PostSchema
from core.exceptions import ChannelNotFound, ScrappingError
from core.logger import get_logger

from .db import get_new_posts_from_posts, add_posts_to_db
from .html_loader import get_channel_info_html
from .parser import parse_channel_posts


logger = get_logger(__name__)


async def update_channel_data(channel_username: str, uow: UOW) -> None:
    """
    Fetch new posts for a channel and save them to the database.

    Args:
        channel_username: The channel's username (without @)
        uow: Unit of Work instance for database operations
    """
    new_posts = await get_channel_new_posts(channel_username, uow)
    if new_posts:
        add_posts_to_db(new_posts, uow)
        logger.info(f"Updated channel @{channel_username} with {len(new_posts)} new posts")
    else:
        logger.info(f"No new posts for channel @{channel_username}")


async def get_channel_new_posts(channel_username: str, uow: UOW) -> List[PostSchema]:
    """
    Fetch and return only new posts for a channel (not yet in DB).

    Args:
        channel_username: The channel's username (without @)
        uow: Unit of Work instance for database operations

    Returns:
        List of new PostSchema objects

    Raises:
        ChannelNotFound: If the channel doesn't exist on TGStat
    """
    try:
        html = await get_channel_info_html(channel_username)
    except ChannelNotFound:
        raise
    except ScrappingError:
        logger.error(
            f"Scrapping error. HTML saved to data/error-{channel_username}.html"
        )
        return []
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return []

    posts = parse_channel_posts(html, channel_username)
    new_posts = get_new_posts_from_posts(posts, channel_username, uow)
    return new_posts
