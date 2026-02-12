# core/event_consumer.py

import asyncio
import json

from aio_pika import connect_robust, IncomingMessage
from dishka import AsyncContainer

from core.config.settings import Settings
from core.database.uow import UnitOfWork
from utils import setup_logger

logger = setup_logger()


class EventConsumer:
    def __init__(self, settings: Settings, container: AsyncContainer):
        self._url = settings.RABBITMQ_URL
        self._container = container

    async def run(self):
        connection = await self._connect()

        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("events_queue", durable=True)
            await queue.consume(self._on_message, no_ack=False)
            logger.info("Консюмер запущен")
            await asyncio.Future()

    async def _connect(self):
        for i in range(20):
            try:
                return await connect_robust(self._url)
            except Exception:
                logger.warning(f"Нет связи с RabbitMQ ({i+1}/20), ждём 3s...")
                await asyncio.sleep(3)
        raise RuntimeError("Не удалось подключиться к RabbitMQ")

    async def _on_message(self, message: IncomingMessage):
        async with message.process():
            try:
                payload = json.loads(message.body)
                logger.info(f"Событие: {payload}")
                await self._handle(payload)
            except Exception as e:
                logger.error(f"Ошибка обработки: {e}", exc_info=True)
                raise

    async def _handle(self, payload: dict):
        if payload.get("type") == "mark_post":
            async with self._container() as req:
                uow = await req.get(UnitOfWork)
                await uow.posts.update(
                    payload["post_id"],
                    payload["channel_username"],
                    mark=payload["mark"],
                )
                await uow.commit()
