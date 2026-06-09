from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    BOT_TOKEN: str
    SCRAPPER_API_URL: str

    ENABLE_BOT: bool
    ENABLE_SCHEDULER: bool
