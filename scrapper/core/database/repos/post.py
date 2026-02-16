from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Post


class PostRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, **kwargs) -> Post:
        post = await self.get_one(kwargs['id'], kwargs['channel_username'])
        if post is None:
            post = Post(**kwargs)
            self._session.add(post)
            await self._session.flush()
        return post

    async def get_one(self, id: int, channel_username: str) -> Post | None:
        return await self._session.get(Post, (id, channel_username))

    async def get_many(self, **kwargs) -> list[Post]:
        result = await self._session.execute(
            select(Post).filter_by(**kwargs)
        )
        return list(result.scalars().all())

    async def get_many_with_params(
        self,
        channel_username: str,
        limit: int | None = None,
        order: str = "desc",
        marked: str | None = None,
        unmarked: bool = False,
        created_after: datetime | None = None,
    ) -> list[Post]:
        query = (
            select(Post)
            .options(selectinload(Post.medias))
            .filter_by(channel_username=channel_username)
        )

        if unmarked:
            query = query.filter(Post.mark.is_(None))
        elif marked is not None:
            query = query.filter(Post.mark == marked)

        if created_after is not None:
            query = query.filter(Post.created_at >= created_after)

        if order == "desc":
            query = query.order_by(Post.created_at.desc())
        else:
            query = query.order_by(Post.created_at.asc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, id: int, channel_username: str, **kwargs) -> None:
        post = await self._session.get(Post, (id, channel_username))
        if post:
            for key, value in kwargs.items():
                setattr(post, key, value)

    async def delete(self, id: int, channel_username: str) -> None:
        post = await self._session.get(Post, (id, channel_username))
        if post:
            await self._session.delete(post)
