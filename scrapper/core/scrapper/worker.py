import asyncio
import logging

from dishka import AsyncContainer

from core.database.uow import UnitOfWork
from .service import ScrapperService


logger = logging.getLogger(__name__)


class ScrapperWorker:
    SCRAPPER_DELAY = 45.0  # in seconds
    SCRAPPER_IDLE_DELAY = 60.0  # in seconds

    def __init__(self, container: AsyncContainer):
        self.container = container

    async def run(self):
        while True:
            async with self.container() as scope:
                await self._process_one(scope)
            await asyncio.sleep(self.SCRAPPER_DELAY)

    async def _process_one(self, scope: AsyncContainer):
        uow = await scope.get(UnitOfWork)
        service = await scope.get(ScrapperService)

        channel = await uow.channels.get_next_channel_to_check()

        if channel is None:
            logger.info(f"Каналов для проверки нет. Ждём {self.SCRAPPER_IDLE_DELAY} сек.")
            await asyncio.sleep(self.SCRAPPER_IDLE_DELAY)
            return

        await service.update_data(uow, channel.username)
