from __future__ import annotations
from typing import Optional, TYPE_CHECKING

import datetime as dt

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .channel import Channel
    from .media import Media


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    channel_username: Mapped[str] = mapped_column(
        ForeignKey("channel.username", ondelete="CASCADE"),
        primary_key=True
    )
    mark: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(String, default=None)

    channel: Mapped["Channel"] = relationship(back_populates="posts")
    medias: Mapped[list["Media"]] = relationship(
        "Media",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
