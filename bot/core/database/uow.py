from sqlalchemy.ext.asyncio import AsyncSession

from .repos.channel import ChannelRepository
from .repos.donor import DonorRepository
from .repos.used_post import UsedPostRepository
from .repos.cycle import CycleRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session

        self.channels = ChannelRepository(session)
        self.donors = DonorRepository(session)
        self.used_posts = UsedPostRepository(session)
        self.cycles = CycleRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
