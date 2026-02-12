import asyncio
import logging

from dishka import make_async_container
from typing import Coroutine, List

from sqlalchemy.ext.asyncio import AsyncEngine

from core.runner import AppRunner
from core.config.settings import Settings
from core.database.models.base import Base
import core.database.models  # noqa: F401 — регистрация моделей в Base.metadata
from core.distribution.scheduler import DistributionScheduler
from core.bot.handlers import run_bot

from main_factory import get_all_dishka_providers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def init_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы базы данных созданы")


async def main():
    runner = AppRunner()

    dishka = make_async_container(*get_all_dishka_providers())
    settings = await dishka.get(Settings)

    # Создаём таблицы при старте
    engine = await dishka.get(AsyncEngine)
    await init_database(engine)

    coroutines: List[Coroutine] = []

    if settings.ENABLE_SCHEDULER:
        scheduler = DistributionScheduler(dishka)
        scheduler.start()

    if settings.ENABLE_BOT:
        coroutines.append(run_bot(dishka))

    await runner.run(*coroutines)


if __name__ == "__main__":
    asyncio.run(main())
