from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .donor import Donor


class Channel(Base):
    __tablename__ = "channel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    invite_link: Mapped[Optional[str]] = mapped_column(String, default=None)

    donors: Mapped[list["Donor"]] = relationship(
        "Donor",
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
