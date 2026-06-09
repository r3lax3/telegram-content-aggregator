from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import UsedPost


class UsedPostRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, donor_username: str, post_id: int, mark: str) -> None:
        existing = await self._session.get(UsedPost, (donor_username, post_id))
        if existing:
            existing.mark = mark
            return
        self._session.add(
            UsedPost(donor_username=donor_username, post_id=post_id, mark=mark)
        )
        await self._session.flush()

    async def get_marked_keys(
        self, donor_usernames: list[str]
    ) -> set[tuple[str, int]]:
        if not donor_usernames:
            return set()

        result = await self._session.execute(
            select(UsedPost.donor_username, UsedPost.post_id).where(
                UsedPost.donor_username.in_(donor_usernames)
            )
        )
        return {(row[0], row[1]) for row in result.all()}
