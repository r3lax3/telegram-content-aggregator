from typing import Self

from .repositories import (
    SQLChannelRepository,
    SQLMediaRepository,
    SQLPostRepository
)


class UOW:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self) -> Self:
        self.session = self.session_factory()

        self.channels = SQLChannelRepository(self.session)
        self.posts = SQLPostRepository(self.session)
        self.media = SQLMediaRepository(self.session)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()

        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
