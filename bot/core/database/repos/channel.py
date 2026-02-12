from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, **kwargs) -> Channel:
        channel = Channel(**kwargs)
        self._session.add(channel)
        await self._session.flush()
        return channel

    async def get_one(self, id: int) -> Channel | None:
        return await self._session.get(Channel, id)

    async def get_many(self) -> list[Channel]:
        result = await self._session.execute(select(Channel))
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs) -> None:
        channel = await self._session.get(Channel, id)
        if channel:
            for key, value in kwargs.items():
                setattr(channel, key, value)

    async def delete(self, id: int) -> None:
        channel = await self._session.get(Channel, id)
        if channel:
            await self._session.delete(channel)
