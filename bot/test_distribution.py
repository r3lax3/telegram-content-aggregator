"""
Ручной запуск рассылки постов по каналам.

Использование:
    # Рассылка по ВСЕМ каналам из БД (аналог старого test_posting_globally.py)
    python test_distribution.py

    # Рассылка только в конкретный канал (аналог старого test_posting.py)
    python test_distribution.py --channel -1003091360368

    # Рассылка в конкретный канал в цикле (каждые N секунд)
    python test_distribution.py --channel -1003091360368 --loop --interval 30
"""

import sys
import asyncio
import logging
import argparse

from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine
from aiogram import Bot

from core.config.settings import Settings
from core.database.models.base import Base
import core.database.models  # noqa: F401
from core.database.uow import UnitOfWork
from core.messaging.rabbitmq import RabbitMQPublisher
from core.distribution.distributor import (
    distribute_posts_globally,
    distribute_post_to_channel,
)
from core.distribution.collector import collect_posts_for_channel

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


async def run_global(container) -> None:
    """Запуск рассылки по всем каналам из БД (один раз)."""
    logger.info("Запускаю глобальную рассылку по всем каналам...")
    await distribute_posts_globally(container)
    logger.info("Глобальная рассылка завершена.")


async def run_for_channel(container, channel_id: int, loop: bool, interval: int) -> None:
    """Запуск рассылки в конкретный канал."""
    bot = await container.get(Bot)
    publisher = await container.get(RabbitMQPublisher)
    settings = await container.get(Settings)

    me = await bot.get_me()
    logger.info(f"Бот: @{me.username}")

    while True:
        async with container() as req:
            uow = await req.get(UnitOfWork)
            donors = await uow.donors.get_many(channel_id=channel_id)
            donor_usernames = [d.username for d in donors]

        if not donor_usernames:
            logger.error(
                f"У канала {channel_id} нет доноров в БД. "
                "Добавьте доноров через бота или напрямую в базу."
            )
            return

        logger.info(
            f"Канал {channel_id}, доноры: {donor_usernames}. "
            "Собираю посты..."
        )

        posts = await collect_posts_for_channel(
            settings.SCRAPPER_API_URL, donor_usernames
        )
        logger.info(f"Собрано {len(posts)} постов.")

        await distribute_post_to_channel(
            container, bot, publisher, channel_id, posts
        )
        logger.info("Рассылка в канал завершена.")

        if not loop:
            break

        logger.info(f"Следующий цикл через {interval} сек...")
        await asyncio.sleep(interval)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ручной запуск рассылки постов по каналам."
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=None,
        help="ID целевого канала. Если не указан — рассылка по всем каналам из БД.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Повторять рассылку в цикле (только с --channel).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Интервал между циклами в секундах (по умолчанию 30).",
    )
    args = parser.parse_args()

    dishka = make_async_container(*get_all_dishka_providers())

    engine = await dishka.get(AsyncEngine)
    await init_database(engine)

    try:
        if args.channel is None:
            await run_global(dishka)
        else:
            await run_for_channel(dishka, args.channel, args.loop, args.interval)
    except KeyboardInterrupt:
        logger.info("Прервано пользователем.")
    finally:
        await dishka.close()


if __name__ == "__main__":
    asyncio.run(main())
