import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import PostingCycle, CycleChannel


class CycleRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, slot: str) -> PostingCycle | None:
        return await self._session.get(PostingCycle, slot)

    async def create_if_absent(
        self, slot: str, channel_ids: list[int]
    ) -> PostingCycle:
        """Create the cycle and its per-channel rows once.

        Idempotent: if the cycle already exists (e.g. after a restart) it is
        returned untouched so existing per-channel progress is preserved.
        """
        cycle = await self._session.get(PostingCycle, slot)
        if cycle is not None:
            return cycle

        cycle = PostingCycle(slot=slot)
        self._session.add(cycle)
        for channel_id in channel_ids:
            self._session.add(
                CycleChannel(slot=slot, channel_id=channel_id, done=False)
            )
        await self._session.flush()
        return cycle

    async def get_pending_channel_ids(self, slot: str) -> list[int]:
        result = await self._session.execute(
            select(CycleChannel.channel_id)
            .where(CycleChannel.slot == slot)
            .where(CycleChannel.done.is_(False))
            .order_by(CycleChannel.channel_id.asc())
        )
        return [row[0] for row in result.all()]

    async def mark_channel_done(self, slot: str, channel_id: int) -> None:
        row = await self._session.get(CycleChannel, (slot, channel_id))
        if row:
            row.done = True

    async def complete(self, slot: str) -> None:
        cycle = await self._session.get(PostingCycle, slot)
        if cycle:
            cycle.completed_at = dt.datetime.utcnow()

    async def get_incomplete_since(
        self, not_before: dt.datetime
    ) -> PostingCycle | None:
        """Most recent unfinished cycle started at or after ``not_before``.

        Used on startup to resume a run that was interrupted by a restart,
        while ignoring stale cycles from long-past slots.
        """
        result = await self._session.execute(
            select(PostingCycle)
            .where(PostingCycle.completed_at.is_(None))
            .where(PostingCycle.started_at >= not_before)
            .order_by(PostingCycle.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
