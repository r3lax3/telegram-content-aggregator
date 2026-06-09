import asyncio
import logging

from core.api.run import run_api
from core.runner import AppRunner

from main_factory import create_dishka


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main():
    runner = AppRunner()

    dishka = create_dishka()

    logger.info("Запускаем real-time API скраппера")
    try:
        await runner.run(run_api(dishka))
    finally:
        await dishka.close()
        logger.info("Dishka контейнер закрыт")


if __name__ == "__main__":
    asyncio.run(main())
