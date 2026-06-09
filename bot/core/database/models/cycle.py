from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PostingCycle(Base):
    """One scheduled distribution run (a single time slot, e.g. 08:00).

    Progress is persisted so a restart mid-run can resume from where it left
    off instead of restarting or skipping the slot entirely.
    """

    __tablename__ = "posting_cycle"

    slot: Mapped[str] = mapped_column(String, primary_key=True)  # "2026-06-09-08"
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime, default=None
    )

    channels: Mapped[list["CycleChannel"]] = relationship(
        "CycleChannel",
        back_populates="cycle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CycleChannel(Base):
    """Per-channel progress within a posting cycle."""

    __tablename__ = "posting_cycle_channel"

    slot: Mapped[str] = mapped_column(
        String,
        ForeignKey("posting_cycle.slot", ondelete="CASCADE"),
        primary_key=True,
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    cycle: Mapped["PostingCycle"] = relationship(back_populates="channels")
