from typing import Optional, List

from core.domain.entities import Channel, Post

from .base import ChannelBaseRepository


class SQLChannelRepository(ChannelBaseRepository[Channel]):
    def __init__(self, session):
        self.session = session

    def add(self, **kwargs) -> Channel:
        channel = Channel(**kwargs)

        self.session.add(channel)
        self.session.commit()
        self.session.refresh(channel)

        return channel

    def get_one(self, username: str, **kwargs) -> Optional[Channel]:
        return self.session.query(Channel).filter_by(
            username=username,
            **kwargs
        ).one_or_none()

    def get_many(self, **kwargs) -> List[Channel]:
        return self.session.query(Channel).filter_by(**kwargs).all()

    def get_channels_ordered_by_last_updates_check(self):
        return self.session.query(Channel).order_by(
            Channel.last_update_check.desc()
        ).all()

    # scrapper/domain/repositories.py
    def get_next_channel_to_check(self) -> Channel | None:
        return (
            self.session.query(Channel)
            .order_by(Channel.last_update_check.asc().nulls_first())
            .first()
        )

    def get_last_post(self, username: str):
        return (
            self.session
            .query(Post)
            .filter_by(channel_username=username)
            .order_by(Post.id.desc())
            .first()
        )

    def update(self, username: str, **kwargs) -> None:
        channel = self.session.query(Channel).filter_by(username=username).one_or_none()
        if channel:
            for key, value in kwargs.items():
                if hasattr(channel, key):
                    setattr(channel, key, value)
            self.session.commit()

    def delete(self, username: str) -> None:
        channel = self.session.query(Channel).filter_by(username=username).one_or_none()
        if channel:
            self.session.delete(channel)
            self.session.commit()
