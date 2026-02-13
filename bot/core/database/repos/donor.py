from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Donor


class DonorRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, **kwargs) -> Donor:
        donor = Donor(**kwargs)
        self._session.add(donor)
        await self._session.flush()
        return donor

    async def get_one(self, username: str, channel_id: int) -> Donor | None:
        return await self._session.get(Donor, (username, channel_id))

    async def get_many(self, **kwargs) -> list[Donor]:
        result = await self._session.execute(
            select(Donor).filter_by(**kwargs)
        )
        return list(result.scalars().all())

    async def update(self, username: str, channel_id: int, **kwargs) -> None:
        donor = await self._session.get(Donor, (username, channel_id))
        if donor:
            for key, value in kwargs.items():
                setattr(donor, key, value)

    async def delete(self, username: str, channel_id: int) -> None:
        donor = await self._session.get(Donor, (username, channel_id))
        if donor:
            await self._session.delete(donor)
