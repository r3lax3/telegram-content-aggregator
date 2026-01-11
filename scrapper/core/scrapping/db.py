from typing import List

from sqlalchemy.exc import IntegrityError

from core.domain import UOW
from core.domain.entities import Post
from core.dto import PostSchema
from core.logger import get_logger


logger = get_logger(__name__)


def get_new_posts_from_posts(
    posts: List[PostSchema],
    channel_username: str,
    uow: UOW,
) -> List[PostSchema]:
    """Filter posts to return only new ones (not yet in DB)."""
    with uow:
        channel = uow.channels.get_one(channel_username)
        if channel is None:
            raise Exception(f"Channel {channel_username} not found in database")

        last_post = uow.channels.get_last_post(channel_username)
        if last_post is not None:
            # new_posts — those with id > last_post.id
            new_posts = [post for post in posts if post.id > last_post.id]
        else:
            # If no old posts exist — all are considered new
            new_posts = posts

    return new_posts


def add_posts_to_db(posts: List[PostSchema], uow: UOW) -> None:
    """Add posts and their media to the database."""
    if not posts:
        return

    with uow:
        channel_username = posts[0].channel_username
        channel = uow.channels.get_one(channel_username)

        if not channel:
            uow.channels.add(username=channel_username)

        for post_schema in posts:
            try:
                post = uow.posts.add(
                    id=post_schema.id,
                    created_at=post_schema.created_at,
                    channel_username=post_schema.channel_username,
                    mark=post_schema.mark,
                    text=post_schema.text,
                )

                for media_schema in post_schema.medias:
                    uow.media.add(
                        post_id=post.id,
                        post_channel_username=post.channel_username,
                        type=media_schema.type,
                        url=media_schema.url,
                    )

            except IntegrityError:
                uow.rollback()
                continue

        uow.commit()

    logger.info(f"Added {len(posts)} posts to database")
