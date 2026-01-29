from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Enum, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from core.enums import MediaTypeEnum


if TYPE_CHECKING:
    from .post import Post


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer)
    post_channel_username: Mapped[str] = mapped_column(String)
    type: Mapped[MediaTypeEnum] = mapped_column(Enum(MediaTypeEnum))
    url: Mapped[str] = mapped_column(String)

    post: Mapped["Post"] = relationship(back_populates="medias")

    __table_args__ = (
        ForeignKeyConstraint(
            ["post_id", "post_channel_username"],
            ["post.id", "post.channel_username"],
            ondelete="CASCADE"
        ),
    )
