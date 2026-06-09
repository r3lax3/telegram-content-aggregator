from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # The scrapper is now a stateless real-time service: it owns no database
    # and no message queue, so no connection settings are required here.
    pass
