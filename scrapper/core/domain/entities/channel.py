from __future__ import annotations
from typing import Optional, TYPE_CHECKING

import datetime as dt

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .post import Post


class Channel(Base):
    __tablename__ = "channel"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    last_update_check: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)
    last_post_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    posts: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
