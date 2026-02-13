import asyncio
import logging

from dishka import make_async_container
from typing import Coroutine, List

from core.api.run import run_api
from core.runner import AppRunner
from core.config.settings import Settings
from core.scrapper.worker import ScrapperWorker
from core.event_consumer import EventConsumer

from main_factory import get_all_dishka_providers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main():
    runner = AppRunner()

    dishka = make_async_container(*get_all_dishka_providers())
    settings = await dishka.get(Settings)

    logger.info(
        f"Конфиг: loop={settings.ENABLE_SCRAPPER_LOOP}, "
        f"api={settings.ENABLE_API}, consumer={settings.ENABLE_EVENT_CONSUMER}"
    )

    corutines: List[Coroutine] = []

    if settings.ENABLE_SCRAPPER_LOOP:
        worker = await dishka.get(ScrapperWorker)
        corutines.append(worker.run())

    if settings.ENABLE_API:
        corutines.append(run_api())

    if settings.ENABLE_EVENT_CONSUMER:
        consumer = await dishka.get(EventConsumer)
        corutines.append(consumer.run())

    logger.info(f"Запускаем {len(corutines)} компонентов")
    await runner.run(*corutines)


if __name__ == "__main__":
    asyncio.run(main())

