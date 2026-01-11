from typing import List, Optional

from core.domain.entities import Post
from .base import PostBaseRepository


class SQLPostRepository(PostBaseRepository[Post]):
    def __init__(self, session):
        self.session = session

    def add(self, **kwargs) -> Post:
        post = self.get_one(kwargs['id'], kwargs['channel_username'])

        post_not_in_database = post is None
        if post_not_in_database:
            post = Post(**kwargs)
            self.session.add(post)
            self.session.commit()
            self.session.refresh(post)

        return post

    def get_one(
        self,
        id: int,
        channel_username: str,
        **kwargs
    ) -> Optional[Post]:
        return self.session.query(Post).filter_by(
            id=id,
            channel_username=channel_username,
            **kwargs
        ).one_or_none()

    def get_many(self, **kwargs) -> List[Post]:
        return self.session.query(Post).filter_by(**kwargs).all()

    def get_many_with_params(
        self,
        channel_username: str,
        limit: Optional[int] = None,
        order: str = "desc",
        marked: Optional[str] = None
    ):
        query = self.session.query(Post).filter_by(channel_username=channel_username)

        query = query.filter(Post.mark.isnot(None) if marked else Post.mark.is_(None))
        query = query.order_by(Post.created_at.desc() if order == "desc" else Post.created_at.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def update(self, id: int, channel_username: str, **kwargs) -> None:
        post = self.session.query(Post).filter_by(
            id=id,
            channel_username=channel_username
        ).one_or_none()

        if post:
            for key, value in kwargs.items():
                if hasattr(post, key):
                    setattr(post, key, value)

    def delete(self, id: int, channel_username: str) -> None:
        post = self.session.query(Post).filter_by(id=id, channel_username=channel_username).one_or_none()
        if post:
            self.session.delete(post)
