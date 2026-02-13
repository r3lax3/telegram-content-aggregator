import logging

from aiogram import Bot
from dishka import AsyncContainer

from core.enums import MediaType
from core.schemas.post import PostSchema
from core.database.uow import UnitOfWork
from .content import prepare_text


logger = logging.getLogger(__name__)


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
        await bot.send_message(
            chat_id=channel_id,
            text=text,
            disable_web_page_preview=True
        )
        return

    media = post.medias[0]
    url = media.url

    match media.type:
        case MediaType.IMAGE:
            await bot.send_photo(
                chat_id=channel_id,
                photo=url,
                caption=text,
            )

        case MediaType.VIDEO:
            await bot.send_video(
                chat_id=channel_id,
                video=url,
                caption=text
            )
        case _:
            logger.error(f"Неизвестный тип медиа: {media.type} для канала {channel_id}")
            raise ValueError(f"Unsupported media type: {media.type}")

    logger.info("Сообщение отправлено.")


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
