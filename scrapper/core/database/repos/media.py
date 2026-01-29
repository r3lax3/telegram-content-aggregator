from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Media


class MediaRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, **kwargs) -> Media:
        media = Media(**kwargs)
        self._session.add(media)
        await self._session.flush()
        return media

    async def get_one(self, id: int) -> Media | None:
        return await self._session.get(Media, id)

    async def get_many(self, **kwargs) -> list[Media]:
        result = await self._session.execute(
            select(Media).filter_by(**kwargs)
        )
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs) -> None:
        media = await self._session.get(Media, id)
        if media:
            for key, value in kwargs.items():
                setattr(media, key, value)

    async def delete(self, id: int) -> None:
        media = await self._session.get(Media, id)
        if media:
            await self._session.delete(media)
