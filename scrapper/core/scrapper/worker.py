import asyncio
import logging
import time

import datetime as dt

from dishka import AsyncContainer

from core.database.uow import UnitOfWork
from core.exceptions import ChannelNotFound, ScrappingError
from .service import ScrapperService


logger = logging.getLogger(__name__)


class ScrapperWorker:
    SCRAPPER_DELAY = 45.0  # in seconds
    SCRAPPER_IDLE_DELAY = 60.0  # in seconds

    def __init__(self, container: AsyncContainer):
        self.container = container

    async def run(self):
        logger.info(f"Воркер запущен (интервал {self.SCRAPPER_DELAY} сек)")
        while True:
            try:
                async with self.container() as scope:
                    await self._process_one(scope)
            except Exception as e:
                logger.error(f"[WORKER] Критическая ошибка в цикле: {e}", exc_info=True)
            await asyncio.sleep(self.SCRAPPER_DELAY)

    async def _process_one(self, scope: AsyncContainer):
        uow = await scope.get(UnitOfWork)

        channel = await uow.channels.get_next_channel_to_check()

        if channel is None:
            logger.info(f"Каналов для проверки нет. Ждём {self.SCRAPPER_IDLE_DELAY} сек.")
            await asyncio.sleep(self.SCRAPPER_IDLE_DELAY)
            return

        last_check = channel.last_update_check
        last_check_str = last_check.strftime("%Y-%m-%d %H:%M:%S") if last_check else "никогда"
        logger.info(f"[CHECK] Начинаем проверку @{channel.username} (последняя: {last_check_str})")

        service = await scope.get(ScrapperService)

        started = time.monotonic()
        try:
            await service.update_data(uow, channel.username)
            elapsed = time.monotonic() - started
            logger.info(f"[CHECK] @{channel.username} — проверка завершена за {elapsed:.1f} сек")
        except ChannelNotFound:
            elapsed = time.monotonic() - started
            logger.warning(f"[CHECK] @{channel.username} — канал не найден ({elapsed:.1f} сек)")
        except ScrappingError as e:
            elapsed = time.monotonic() - started
            logger.error(f"[CHECK] @{channel.username} — ошибка скраппинга ({elapsed:.1f} сек): {e}")
        except Exception as e:
            elapsed = time.monotonic() - started
            logger.error(f"[CHECK] @{channel.username} — неожиданная ошибка ({elapsed:.1f} сек): {e}")
        finally:
            await uow.channels.update(channel.username, last_update_check=dt.datetime.utcnow())
            await uow.commit()
