import datetime as dt

from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UsedPost(Base):
    """A donor post the bot has already handled.

    Replaces the old scrapper-side ``mark`` column. Tracking lives in the bot
    now that the scrapper is stateless. Keyed per donor post (globally across
    target channels), matching the previous behaviour where a post used once
    was never served again.
    """

    __tablename__ = "used_post"

    donor_username: Mapped[str] = mapped_column(String, primary_key=True)
    post_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mark: Mapped[str] = mapped_column(String)  # "used" | "ad"
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )
