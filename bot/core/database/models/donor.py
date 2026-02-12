from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .channel import Channel


class Donor(Base):
    __tablename__ = "donor"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channel.id", ondelete="CASCADE"),
        primary_key=True
    )

    channel: Mapped["Channel"] = relationship(back_populates="donors")
