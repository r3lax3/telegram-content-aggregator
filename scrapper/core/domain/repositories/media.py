from typing import Optional, List

from core.domain.entities import Media

from .base import BaseRepository


class SQLMediaRepository(BaseRepository[Media]):
    def __init__(self, session):
        self.session = session

    def add(self, **kwargs) -> Media:
        media = Media(**kwargs)

        self.session.add(media)
        self.session.commit()
        self.session.refresh(media)

        return media

    def get_one(self, id: int, **kwargs) -> Optional[Media]:
        return self.session.query(Media).filter_by(id=id, **kwargs).one_or_none()

    def get_many(self, **kwargs) -> List[Media]:
        return self.session.query(Media).filter_by(**kwargs).all()

    def update(self, id: int, **kwargs) -> None:
        media = self.session.query(Media).filter_by(id=id).one_or_none()
        if media:
            for key, value in kwargs.items():
                if hasattr(media, key):
                    setattr(media, key, value)
            self.session.commit()

    def delete(self, id: int) -> None:
        media = self.session.query(Media).filter_by(id=id).one_or_none()
        if media:
            self.session.delete(media)
            self.session.commit()
