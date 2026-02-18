from typing import List, AsyncIterable

from dishka import Provider, Scope
from core.config.settings import Settings

from dishka import (
    Provider,
    Scope,
    AsyncContainer,
    STRICT_VALIDATION,
    provide,
    make_async_container,
)

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config.settings import Settings
from core.scrapper.worker import ScrapperWorker
from core.scrapper.service import ScrapperService
from core.database.uow import UnitOfWork
from core.scrapper.browser import PlaywrightManager
from core.event_consumer import EventConsumer


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


class WorkerProvider(Provider):
    scope = Scope.APP

    @provide
    def get_scrapper_worker(self, container: AsyncContainer) -> ScrapperWorker:
        return ScrapperWorker(container)


class ScrapperServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_scrapper_service(self, pw_manager: PlaywrightManager) -> ScrapperService:
        return ScrapperService(pw_manager)


class PlaywrightProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_playwright_manager(self) -> AsyncIterable[PlaywrightManager]:
        async with PlaywrightManager() as pm:
            yield pm


class EventConsumerProvider(Provider):
    scope = Scope.APP

    @provide
    def get_event_consumer(self, settings: Settings, container: AsyncContainer) -> EventConsumer:
        return EventConsumer(settings, container)


def get_all_dishka_providers() -> List[Provider]:
    return [
        ConfigProvider(),
        DatabaseProvider(),
        SessionProvider(),
        UOWProvider(),
        WorkerProvider(),
        ScrapperServiceProvider(),
        PlaywrightProvider(),
        EventConsumerProvider(),
    ]


def create_dishka() -> AsyncContainer:
    container = make_async_container(
        *get_all_dishka_providers(),
        validation_settings=STRICT_VALIDATION
    )
    return container
