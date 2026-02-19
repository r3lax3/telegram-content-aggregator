"""
Тест доступа бота к каналам из БД.

Проверяет для каждого канала из базы данных:
- Есть ли бот в канале
- Имеет ли бот права администратора
- Какие именно права у бота (отправка сообщений, редактирование и т.д.)

Запуск:
    pytest test_channel_access.py -v -s
    python test_channel_access.py
"""

import asyncio
import logging
import sys
from dataclasses import dataclass, field

from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine
from aiogram import Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
)

from core.config.settings import Settings
from core.database.models.base import Base
import core.database.models  # noqa: F401
from core.database.uow import UnitOfWork
from main_factory import get_all_dishka_providers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@dataclass
class ChannelAccessResult:
    channel_id: int
    is_member: bool = False
    is_admin: bool = False
    status: str = "unknown"
    chat_title: str | None = None
    error: str | None = None
    admin_rights: dict[str, bool] = field(default_factory=dict)


async def check_channel_access(bot: Bot, channel_id: int) -> ChannelAccessResult:
    """Проверяет доступ бота к конкретному каналу."""
    result = ChannelAccessResult(channel_id=channel_id)

    try:
        chat = await bot.get_chat(channel_id)
        result.chat_title = chat.title
    except (TelegramBadRequest, TelegramForbiddenError, TelegramNotFound) as e:
        result.error = f"Нет доступа к каналу: {e}"
        return result
    except Exception as e:
        result.error = f"Неизвестная ошибка при get_chat: {e}"
        return result

    try:
        me = await bot.me()
        member = await bot.get_chat_member(channel_id, me.id)
        result.status = member.status

        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            result.is_member = True
            result.is_admin = True

            if isinstance(member, ChatMemberAdministrator):
                result.admin_rights = {
                    "can_post_messages": member.can_post_messages or False,
                    "can_edit_messages": member.can_edit_messages or False,
                    "can_delete_messages": member.can_delete_messages or False,
                    "can_invite_users": member.can_invite_users or False,
                    "can_manage_chat": member.can_manage_chat or False,
                }
        elif member.status == "member":
            result.is_member = True
        # left, kicked, restricted — бот не полноценный участник

    except (TelegramBadRequest, TelegramForbiddenError, TelegramNotFound) as e:
        result.error = f"Ошибка при проверке членства: {e}"
    except Exception as e:
        result.error = f"Неизвестная ошибка при get_chat_member: {e}"

    return result


async def check_all_channels() -> list[ChannelAccessResult]:
    """Получает все каналы из БД и проверяет доступ бота к каждому."""
    dishka = make_async_container(*get_all_dishka_providers())

    try:
        engine = await dishka.get(AsyncEngine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        bot = await dishka.get(Bot)
        me = await bot.me()
        logger.info(f"Бот: @{me.username} (ID: {me.id})")

        async with dishka() as req:
            uow = await req.get(UnitOfWork)
            channels = await uow.channels.get_many()

        if not channels:
            logger.warning("В базе данных нет каналов.")
            return []

        logger.info(f"Найдено каналов в БД: {len(channels)}")

        results: list[ChannelAccessResult] = []
        for channel in channels:
            result = await check_channel_access(bot, channel.id)
            results.append(result)

        return results

    finally:
        await dishka.close()


def print_report(results: list[ChannelAccessResult]) -> None:
    """Выводит отчёт о доступе бота к каналам."""
    if not results:
        print("\n❌ Каналов в базе данных не найдено.")
        return

    ok: list[ChannelAccessResult] = []
    no_admin: list[ChannelAccessResult] = []
    no_access: list[ChannelAccessResult] = []

    for r in results:
        if r.is_admin:
            ok.append(r)
        elif r.is_member:
            no_admin.append(r)
        else:
            no_access.append(r)

    print("\n" + "=" * 60)
    print(f"  ОТЧЁТ О ДОСТУПЕ БОТА К КАНАЛАМ ({len(results)} шт.)")
    print("=" * 60)

    # --- Каналы с полным доступом ---
    if ok:
        print(f"\n✅ Бот — администратор ({len(ok)}):")
        for r in ok:
            title = r.chat_title or "N/A"
            print(f"   {r.channel_id}  {title}")
            if r.admin_rights:
                missing = [k for k, v in r.admin_rights.items() if not v]
                if missing:
                    print(f"      ⚠ Нет прав: {', '.join(missing)}")

    # --- Бот есть, но не админ ---
    if no_admin:
        print(f"\n⚠ Бот в канале, но НЕ администратор ({len(no_admin)}):")
        for r in no_admin:
            title = r.chat_title or "N/A"
            print(f"   {r.channel_id}  {title}  (статус: {r.status})")

    # --- Нет доступа ---
    if no_access:
        print(f"\n❌ Бот НЕ в канале / нет доступа ({len(no_access)}):")
        for r in no_access:
            title = r.chat_title or "N/A"
            err = r.error or f"статус: {r.status}"
            print(f"   {r.channel_id}  {title}  ({err})")

    # --- Итого ---
    print("\n" + "-" * 60)
    print(f"  Итого: ✅ {len(ok)}  ⚠ {len(no_admin)}  ❌ {len(no_access)}")
    print("-" * 60 + "\n")


# ───────────────────────── pytest ─────────────────────────

import pytest  # noqa: E402


@pytest.mark.asyncio
async def test_bot_has_access_to_all_channels():
    """
    Интеграционный тест: проверяет, что бот является
    администратором во всех каналах из базы данных.

    Запуск: pytest test_channel_access.py -v -s
    """
    results = await check_all_channels()
    print_report(results)

    assert results, "В базе данных нет ни одного канала"

    no_access = [r for r in results if not r.is_member]
    no_admin = [r for r in results if r.is_member and not r.is_admin]
    no_post = [
        r for r in results
        if r.is_admin and not r.admin_rights.get("can_post_messages", True)
    ]

    errors: list[str] = []

    if no_access:
        ids = ", ".join(str(r.channel_id) for r in no_access)
        errors.append(f"Бот отсутствует в каналах: {ids}")

    if no_admin:
        ids = ", ".join(str(r.channel_id) for r in no_admin)
        errors.append(f"Бот не является админом в каналах: {ids}")

    if no_post:
        ids = ", ".join(str(r.channel_id) for r in no_post)
        errors.append(f"У бота нет права отправлять сообщения в каналах: {ids}")

    assert not errors, "\n".join(errors)


# ───────────────────────── standalone ─────────────────────────

async def main() -> None:
    results = await check_all_channels()
    print_report(results)


if __name__ == "__main__":
    asyncio.run(main())
