from sqlalchemy.ext.asyncio import AsyncSession

from .repos.channel import ChannelRepository
from .repos.post import PostRepository
from .repos.media import MediaRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session

        self.channels = ChannelRepository(session)
        self.posts = PostRepository(session)
        self.media = MediaRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
