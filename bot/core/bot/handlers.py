import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dishka import AsyncContainer


logger = logging.getLogger(__name__)


async def run_bot(container: AsyncContainer) -> None:
    bot = await container.get(Bot)
    dp = Dispatcher()

    logger.info("Бот инициализирован, настраиваю обработчики...")

    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
        await message.answer("Статус - активен.")

    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.me()
    logger.info(f"Запускаю поллинг бота (@{me.username})...")
    await dp.start_polling(bot)
