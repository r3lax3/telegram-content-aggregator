from sqlalchemy import select
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
        marked: str | None = None
    ) -> list[Post]:
        query = select(Post).filter_by(channel_username=channel_username)

        if marked:
            query = query.filter(Post.mark.isnot(None))
        else:
            query = query.filter(Post.mark.is_(None))

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
