from typing import List

from dishka import (
    Provider,
    Scope,
    AsyncContainer,
    STRICT_VALIDATION,
    provide,
    make_async_container,
)

from core.config.settings import Settings
from core.scrapper.service import ScrapperService


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def get_settings(self) -> Settings:
        return Settings()  # type: ignore


class ScrapperServiceProvider(Provider):
    scope = Scope.APP

    @provide
    def get_scrapper_service(self) -> ScrapperService:
        return ScrapperService()


def get_all_dishka_providers() -> List[Provider]:
    return [
        ConfigProvider(),
        ScrapperServiceProvider(),
    ]


def create_dishka() -> AsyncContainer:
    container = make_async_container(
        *get_all_dishka_providers(),
        validation_settings=STRICT_VALIDATION
    )
    return container
