import asyncio
import json
import os

from aio_pika import connect_robust, IncomingMessage

from core.logger import get_logger
from core.db import SessionLocal
from core.domain import UOW

logger = get_logger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


async def run_rabbitmq_consumer(stop_event: asyncio.Event):
    """Main RabbitMQ consumer coroutine."""
    connection = await _get_rabbitmq_connection()

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue("events_queue", durable=True)

        async def on_message(message: IncomingMessage):
            await _process_event(message)

        await queue.consume(on_message, no_ack=False)
        logger.info("RabbitMQ consumer started")

        await stop_event.wait()

    logger.info("RabbitMQ consumer stopped")


async def _get_rabbitmq_connection():
    """Establish connection to RabbitMQ with retry logic."""
    retry_delay = 3
    max_retries = 20

    for attempt in range(max_retries):
        try:
            connection = await connect_robust(RABBITMQ_URL)
            logger.info("Connected to RabbitMQ")
            return connection
        except Exception as e:
            logger.warning(
                f"RabbitMQ connection failed ({attempt + 1}/{max_retries}): {e}, "
                f"retrying in {retry_delay}s..."
            )
            await asyncio.sleep(retry_delay)

    raise RuntimeError("Failed to connect to RabbitMQ after max retries")


async def _process_event(message: IncomingMessage):
    """Process incoming RabbitMQ message."""
    async with message.process():
        try:
            payload = json.loads(message.body)
            event_type = payload.get("type")
            logger.info(f"Received event: {event_type}")

            if event_type == "mark_post":
                await _handle_mark_post(
                    post_id=payload["post_id"],
                    channel_username=payload["channel_username"],
                    mark=payload["mark"],
                )
            else:
                logger.warning(f"Unknown event type: {event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in payload: {e}")
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            raise


async def _handle_mark_post(post_id: int, channel_username: str, mark: str):
    """Handle mark_post event by updating post in database."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _mark_post_sync,
        post_id,
        channel_username,
        mark,
    )
    logger.info(f"Marked post {post_id} in {channel_username} as '{mark}'")


def _mark_post_sync(post_id: int, channel_username: str, mark: str):
    """Synchronous database operation to mark a post."""
    with UOW(session_factory=SessionLocal) as uow:
        uow.posts.update(post_id, channel_username, mark=mark)
        uow.commit()
