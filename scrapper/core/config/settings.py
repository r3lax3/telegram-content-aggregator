from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    ENABLE_API: bool
    ENABLE_EVENT_CONSUMER: bool
    ENABLE_SCRAPPER_LOOP: bool
