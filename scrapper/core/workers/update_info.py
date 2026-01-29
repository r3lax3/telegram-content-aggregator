import asyncio
import datetime as dt

from core.domain.uow import UOW
from core.scrapping.core import update_channel_data
from core.exceptions import ChannelNotFound, ParsingError, RobotSuspition

from core.logger import get_logger


logger = get_logger(__name__)


async def run_update_info_worker(uow: UOW, interval: float = 60.0, empty_retry_delay: float = 60.0):
    logger.info("ChannelCheckWorker запущен")

    while True:
        username = await _get_channel_to_check(uow)

        if username is None:
            logger.info(f"Каналов для проверки нет. Ждём {empty_retry_delay} сек.")
            await asyncio.sleep(empty_retry_delay)
            continue

        try:
            await _check_and_update(uow, username)
            logger.info(f"Успешно проверен @{username}")

        except ChannelNotFound:
            logger.info(f"Канал @{username} не обнаружен на tgstat.ru")

        except RobotSuspition:
            logger.info(f"При скрапинге канала @{username} вернуло ошибку 429 (Подозрение в роботоводстве)")

        except ParsingError:
            logger.info(f"Ошибка при парсинге канала @{username}. Документ сохранён в файл error_{username}.html")

        except Exception as e:
            logger.error(f"Ошибка при проверке @{username}: {e}", exc_info=True)
            # Продолжаем — один сбой не должен убить воркер

        await asyncio.sleep(interval)


async def _get_channel_to_check(uow: UOW) -> str | None:
    """Возвращает username канала, который нужно проверить, или None"""
    with uow as uow:
        channel = uow.channels.get_next_channel_to_check()
        return channel.username if channel else None


async def _check_and_update(uow: UOW, username: str):
    """Проверка + обновление времени"""
    with uow as uow:
        try:
            await update_channel_data(username, uow)

        except Exception:
            raise

        finally:
            uow.channels.update(username, last_update_check=dt.datetime.now(dt.UTC))
