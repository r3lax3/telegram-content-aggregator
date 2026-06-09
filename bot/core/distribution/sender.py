import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError
from aiogram.types import InputMediaPhoto, InputMediaVideo
from dishka import AsyncContainer

from core.enums import MediaType
from core.schemas.post import PostSchema
from core.schemas.media import MediaSchema
from core.database.uow import UnitOfWork
from .content import prepare_text


logger = logging.getLogger(__name__)


# Transient-failure retries. Telegram CDN URLs scraped in real time stay valid
# for a couple of minutes, so a short retry window lets one hiccup recover
# without losing the post for this cycle.
SEND_RETRIES = 4
SEND_BACKOFF_BASE = 10  # seconds: 10, 20, 30 ...
ALBUM_MAX_SIZE = 10

T = TypeVar("T")


async def _send_with_retry(make_coro: Callable[[], Awaitable[T]]) -> T:
    last_error: Exception | None = None

    for attempt in range(1, SEND_RETRIES + 1):
        try:
            return await make_coro()
        except TelegramRetryAfter as e:
            logger.warning(f"Flood control, ждём {e.retry_after}с")
            await asyncio.sleep(e.retry_after)
            last_error = e
        except (TelegramNetworkError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < SEND_RETRIES:
                backoff = SEND_BACKOFF_BASE * attempt
                logger.warning(
                    f"Сетевая ошибка отправки ({attempt}/{SEND_RETRIES}): {e}. "
                    f"Повтор через {backoff}с"
                )
                await asyncio.sleep(backoff)

    assert last_error is not None
    raise last_error


async def send_post_to_channel(
    container: AsyncContainer,
    bot: Bot,
    channel_id: int,
    post: PostSchema,
) -> None:
    logger.info(f"Отправляю сообщение в канал {channel_id} (@{post.channel_username})/{post.id}")

    chat = await bot.get_chat(channel_id)

    channel_name = chat.title
    invite_link = await get_channel_invite_link(container, channel_id, bot)

    text = prepare_text(post.text, invite_link, channel_name)

    if not post.medias:
        await _send_with_retry(
            lambda: bot.send_message(
                chat_id=channel_id,
                text=text,
                disable_web_page_preview=True,
            )
        )
        logger.info("Сообщение отправлено.")
        return

    if len(post.medias) == 1:
        await _send_single_media(bot, channel_id, post.medias[0], text)
    else:
        await _send_album(bot, channel_id, post.medias, text)

    logger.info("Сообщение отправлено.")


async def _send_single_media(
    bot: Bot,
    channel_id: int,
    media: MediaSchema,
    caption: str,
) -> None:
    match media.type:
        case MediaType.IMAGE:
            await _send_with_retry(
                lambda: bot.send_photo(
                    chat_id=channel_id,
                    photo=media.url,
                    caption=caption,
                )
            )
        case MediaType.VIDEO:
            await _send_with_retry(
                lambda: bot.send_video(
                    chat_id=channel_id,
                    video=media.url,
                    caption=caption,
                )
            )
        case _:
            logger.error(f"Неизвестный тип медиа: {media.type} для канала {channel_id}")
            raise ValueError(f"Unsupported media type: {media.type}")


async def _send_album(
    bot: Bot,
    channel_id: int,
    medias: list[MediaSchema],
    caption: str,
) -> None:
    # Telegram allows at most 10 items per media group; larger albums are split
    # into several groups. The caption goes on the very first item only.
    for chunk_index in range(0, len(medias), ALBUM_MAX_SIZE):
        chunk = medias[chunk_index:chunk_index + ALBUM_MAX_SIZE]
        group = []
        for offset, media in enumerate(chunk):
            item_caption = caption if (chunk_index == 0 and offset == 0) else None
            if media.type == MediaType.IMAGE:
                group.append(InputMediaPhoto(media=media.url, caption=item_caption))
            elif media.type == MediaType.VIDEO:
                group.append(InputMediaVideo(media=media.url, caption=item_caption))
            else:
                logger.warning(f"Пропускаю медиа неизвестного типа: {media.type}")

        if group:
            await _send_with_retry(
                lambda g=group: bot.send_media_group(chat_id=channel_id, media=g)
            )


async def get_channel_invite_link(
    container: AsyncContainer,
    channel_id: int,
    bot: Bot,
) -> str:
    async with container() as req:
        uow = await req.get(UnitOfWork)
        channel = await uow.channels.get_one(channel_id)

        if channel and channel.invite_link:
            return channel.invite_link

        invite_link = (
            await bot.create_chat_invite_link(channel_id)
        ).invite_link

        await uow.channels.update(channel_id, invite_link=invite_link)
        await uow.commit()

        return invite_link
