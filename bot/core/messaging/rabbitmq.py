import asyncio
import json
import logging

import aio_pika


logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, url: str):
        self._url = url
        self._connection = None

    async def connect(self) -> None:
        for i in range(20):
            try:
                self._connection = await aio_pika.connect_robust(self._url)
                logger.info("Успешно подключились к RabbitMQ")
                return
            except Exception:
                logger.warning(f"Нет связи с RabbitMQ ({i+1}/20), ждём 3s...")
                await asyncio.sleep(3)
        raise RuntimeError("Не удалось подключиться к RabbitMQ")

    async def publish_event(self, payload: dict, routing_key: str = "events_queue") -> None:
        if not self._connection or self._connection.is_closed:
            raise RuntimeError("RabbitMQ connection is not initialized or closed")

        channel = await self._connection.channel()
        try:
            await channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(payload).encode()),
                routing_key=routing_key,
            )
        finally:
            await channel.close()

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
