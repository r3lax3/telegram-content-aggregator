from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    RABBITMQ_URL: str

    ENABLE_API: bool
    ENABLE_EVENT_CONSUMER: bool
    ENABLE_SCRAPPER_LOOP: bool

    PROXY_SERVER:   str | None
    PROXY_USERNAME: str | None
    PROXY_PASSWORD: str | None
