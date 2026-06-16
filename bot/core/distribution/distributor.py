import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from dishka import AsyncContainer

from core.schemas.post import PostSchema
from core.config.settings import Settings
from core.database.uow import UnitOfWork
from core.exceptions import MediaUnavailableError
from core.distribution.content import delete_bottom_links

from .collector import collect_posts_for_channel
from .ad import is_advertisement
from .sender import send_post_to_channel


logger = logging.getLogger(__name__)


SLOT_TZ = ZoneInfo("Europe/Moscow")
POST_INTERVAL = 40  # seconds between successful sends
# A cycle older than this is considered stale and is not resumed on startup
# (the next slot is only 4 hours away anyway).
RESUME_WINDOW = timedelta(hours=4)


def current_slot() -> str:
    """Identifier for the current scheduling slot, e.g. ``2026-06-09-08``."""
    return datetime.now(SLOT_TZ).strftime("%Y-%m-%d-%H")


async def resume_incomplete_cycle(container: AsyncContainer) -> None:
    """On startup, continue a run that a restart interrupted mid-cycle."""
    async with container() as req:
        uow = await req.get(UnitOfWork)
        not_before = datetime.utcnow() - RESUME_WINDOW
        cycle = await uow.cycles.get_incomplete_since(not_before)

    if cycle is None:
        return

    # The current slot belongs to the scheduler's cron job; only resume an
    # earlier slot that an interrupted run left unfinished.
    if cycle.slot == current_slot():
        return

    logger.info(f"Найден незавершённый цикл {cycle.slot}, возобновляю...")
    await distribute_posts_globally(container, slot=cycle.slot)


async def distribute_posts_globally(
    container: AsyncContainer,
    slot: str | None = None,
) -> None:
    bot = await container.get(Bot)
    settings = await container.get(Settings)

    if slot is None:
        slot = current_slot()

    async with container() as req:
        uow = await req.get(UnitOfWork)
        channels = await uow.channels.get_many()
        channel_ids = [c.id for c in channels]
        await uow.cycles.create_if_absent(slot, channel_ids)
        await uow.commit()
        pending = await uow.cycles.get_pending_channel_ids(slot)

    total = len(channel_ids)
    logger.info(
        f"[cycle {slot}] каналов всего: {total}, осталось обработать: {len(pending)}"
    )

    successful = 0
    failed = 0

    for index, channel_id in enumerate(pending, start=1):
        logger.info(f"[cycle {slot}] [{index}/{len(pending)}] Рассылка в канал {channel_id}...")

        sent = await _process_channel(container, bot, settings, channel_id)

        async with container() as req:
            uow = await req.get(UnitOfWork)
            await uow.cycles.mark_channel_done(slot, channel_id)
            await uow.commit()

        if sent:
            successful += 1
            await asyncio.sleep(POST_INTERVAL)
        else:
            failed += 1

    async with container() as req:
        uow = await req.get(UnitOfWork)
        await uow.cycles.complete(slot)
        await uow.commit()

    logger.info(
        f"[cycle {slot}] завершён: {successful} успешно, {failed} без отправки "
        f"(каналов в этом проходе: {len(pending)})"
    )


async def _process_channel(
    container: AsyncContainer,
    bot: Bot,
    settings: Settings,
    channel_id: int,
) -> bool:
    async with container() as req:
        uow = await req.get(UnitOfWork)
        donors = await uow.donors.get_many(channel_id=channel_id)
        donor_usernames = [d.username for d in donors]
        marked = await uow.used_posts.get_marked_keys(donor_usernames)

    if not donor_usernames:
        logger.warning(f"Канал {channel_id}: нет доноров, пропускаю")
        return False

    # Fetched in real time so media URLs are seconds old when we post them.
    posts = await collect_posts_for_channel(
        settings.SCRAPPER_API_URL, donor_usernames
    )
    posts = [p for p in posts if (p.channel_username, p.id) not in marked]

    return await distribute_post_to_channel(container, bot, channel_id, posts)


async def distribute_post_to_channel(
    container: AsyncContainer,
    bot: Bot,
    channel_id: int,
    posts: list[PostSchema],
) -> bool:
    retry_on_error_counter = 0

    for post in posts:
        post.text = delete_bottom_links(post.text)

        if not post.text and not post.medias:
            continue

        if post.medias:
            if post.text and len(post.text) > 1024:
                continue

        if is_advertisement(post.text):
            await _mark_post(container, post.channel_username, post.id, "ad")
            logger.info(
                f"Пост {post.id} из канала @{post.channel_username} "
                f"помечен как реклама и не будет отправлен в {channel_id}."
            )
            continue

        try:
            await send_post_to_channel(container, bot, channel_id, post)

        except MediaUnavailableError as e:
            logger.info(
                f"Пост {post.id} (@{post.channel_username}) пропущен — медиа "
                f"недоступно: {e}. Беру следующий пост."
            )
            continue

        except TelegramBadRequest as e:
            logger.warning(
                f"Ошибка TelegramBadRequest для канала {channel_id}: {e}. "
                f"post_id={post.id}, channel=@{post.channel_username}"
            )

        except TelegramForbiddenError as e:
            logger.error(
                f"Ошибка TelegramForbiddenError для канала {channel_id}: {e}. "
                "У бота недостаточно прав для отправки сообщений в канал."
            )
            return False

        except Exception as e:
            logger.error(
                f"Ошибка при отправке поста {post.id} (@{post.channel_username}) "
                f"в канал {channel_id}: {e}",
                exc_info=True,
            )
            retry_on_error_counter += 1
            if retry_on_error_counter < 3:
                continue

        else:
            logger.info(
                f"Пост успешно отправлен в канал {channel_id}:\n"
                f"https://t.me/{post.channel_username}/{post.id}"
            )
            await _mark_post(container, post.channel_username, post.id, "used")
            return True

    logger.error(
        f"В канале {channel_id} не осталось ни одного подходящего поста для публикации. "
        f"Возможные причины: весь контент — реклама или он уже был опубликован."
    )
    return False


async def _mark_post(
    container: AsyncContainer,
    donor_username: str,
    post_id: int,
    mark: str,
) -> None:
    async with container() as req:
        uow = await req.get(UnitOfWork)
        await uow.used_posts.add(donor_username, post_id, mark)
        await uow.commit()
