from typing import List, AsyncIterable

from dishka import (
    Provider,
    Scope,
    AsyncContainer,
    provide,
)

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from core.config.settings import Settings
from core.database.uow import UnitOfWork
from core.messaging.rabbitmq import RabbitMQPublisher


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def get_settings(self) -> Settings:
        return Settings()  # type: ignore


class DatabaseProvider(Provider):
    scope = Scope.APP

    @provide
    def create_engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )

    @provide
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
            autoflush=False,
        )


class SessionProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def create_session(
        self,
        session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session


class UOWProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def create_uow(self, session: AsyncSession) -> UnitOfWork:
        return UnitOfWork(session)


class BotProvider(Provider):
    scope = Scope.APP

    @provide
    def get_bot(self, settings: Settings) -> Bot:
        return Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )


class RabbitMQProvider(Provider):
    scope = Scope.APP

    @provide
    async def get_publisher(self, settings: Settings) -> AsyncIterable[RabbitMQPublisher]:
        publisher = RabbitMQPublisher(settings.RABBITMQ_URL)
        await publisher.connect()
        yield publisher
        await publisher.close()


def get_all_dishka_providers() -> List[Provider]:
    return [
        ConfigProvider(),
        DatabaseProvider(),
        SessionProvider(),
        UOWProvider(),
        BotProvider(),
        RabbitMQProvider(),
    ]
