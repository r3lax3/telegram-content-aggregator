from typing import List, Literal, Optional

from fastapi import APIRouter
from core.dto import PostSchema


router = APIRouter()

@router.get("/posts/", tags=["posts"])
async def get_posts(
    channel: str,
    limit: int = 20,
    order: str = "desc",
    marked: Optional[Literal["used", "ad"]] = None,
) -> List[PostSchema]:
    with UOW() as uow:
        channel_obj = uow.channels.get_one(channel)
        if not channel_obj:
            uow.channels.add(username=channel)

        posts = uow.posts.get_many_with_params(channel, limit, order, marked)

        return posts_models_to_schemas(posts)
