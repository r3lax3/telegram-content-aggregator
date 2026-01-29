from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Channel, Post


class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, **kwargs) -> Channel:
        channel = Channel(**kwargs)
        self._session.add(channel)
        await self._session.flush()
        return channel

    async def get_one(self, username: str) -> Channel | None:
        return await self._session.get(Channel, username)

    async def get_many(self) -> list[Channel]:
        result = await self._session.execute(select(Channel))
        return list(result.scalars().all())

    async def get_next_channel_to_check(self) -> Channel | None:
        result = await self._session.execute(
            select(Channel)
            .order_by(Channel.last_update_check.asc().nulls_first())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_last_post(self, username: str) -> Post | None:
        result = await self._session.execute(
            select(Post)
            .filter_by(channel_username=username)
            .order_by(Post.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, username: str, **kwargs) -> None:
        channel = await self._session.get(Channel, username)
        if channel:
            for key, value in kwargs.items():
                setattr(channel, key, value)

    async def delete(self, username: str) -> None:
        channel = await self._session.get(Channel, username)
        if channel:
            await self._session.delete(channel)
