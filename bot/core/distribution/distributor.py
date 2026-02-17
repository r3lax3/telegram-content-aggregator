import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from dishka import AsyncContainer

from core.schemas.post import PostSchema
from core.config.settings import Settings
from core.database.uow import UnitOfWork
from core.messaging.rabbitmq import RabbitMQPublisher
from core.distribution.content import delete_bottom_links

from .collector import collect_posts_for_channel
from .ad import is_advertisement
from .sender import send_post_to_channel


logger = logging.getLogger(__name__)


async def distribute_posts_globally(container: AsyncContainer) -> None:
    bot = await container.get(Bot)
    publisher = await container.get(RabbitMQPublisher)
    settings = await container.get(Settings)

    result = {}

    async with container() as req:
        uow = await req.get(UnitOfWork)
        channels = await uow.channels.get_many()

        for channel in channels:
            donors = await uow.donors.get_many(channel_id=channel.id)
            donor_usernames = [d.username for d in donors]
            result[channel.id] = await collect_posts_for_channel(
                settings.SCRAPPER_API_URL, donor_usernames
            )

    total = len(result)
    successful = 0
    failed = 0

    for index, (channel_id, posts) in enumerate(result.items(), start=1):
        logger.info(f"[{index}/{total}] Рассылка в канал {channel_id}...")

        sent = await distribute_post_to_channel(
            container, bot, publisher, channel_id, posts
        )
        if sent:
            successful += 1
            await asyncio.sleep(40)
        else:
            failed += 1

    logger.info(
        f"Рассылка завершена: {successful} успешно, {failed} с ошибкой "
        f"(всего каналов: {total})"
    )


async def distribute_post_to_channel(
    container: AsyncContainer,
    bot: Bot,
    publisher: RabbitMQPublisher,
    channel_id: int,
    posts: list[PostSchema],
) -> bool | None:
    retry_on_error_counter = 0

    for post in posts:
        post.text = delete_bottom_links(post.text)

        if not post.text and not post.medias:
            continue

        if post.medias:
            if post.text and len(post.text) > 1024:
                continue

        if is_advertisement(post.text):
            payload = {
                "type": "mark_post",
                "mark": "ad",
                "post_id": post.id,
                "channel_username": post.channel_username,
            }
            await publisher.publish_event(payload)

            logger.info(
                f"Пост {post.id} из канала @{post.channel_username} "
                f"помечен как реклама и не будет отправлен в {channel_id}."
            )

            continue

        try:
            await send_post_to_channel(container, bot, channel_id, post)

        except TelegramBadRequest as e:
            logger.warning(
                f"Ошибка TelegramBadRequest для канала {channel_id}: {e}. "
                f"Пост: {post}"
            )

        except TelegramForbiddenError as e:
            logger.error(
                f"Ошибка TelegramForbiddenError для канала {channel_id}: {e}. "
                "У бота недостаточно прав для отправки сообщений в канал."
            )

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            retry_on_error_counter += 1
            if retry_on_error_counter < 3:
                continue

        else:
            logger.info(
                f"Пост успешно отправлен в канал {channel_id}:\n"
                f"https://tgstat.ru/channel/@{post.channel_username}/{post.id}"
            )

            payload = {
                "type": "mark_post",
                "mark": "used",
                "post_id": post.id,
                "channel_username": post.channel_username,
            }
            await publisher.publish_event(payload)
            return True

    else:
        logger.error(
            f"В канале {channel_id} не осталось ни одного подходящего поста для публикации. "
            f"Возможные причины: весь контент — реклама или он уже был опубликован."
        )
