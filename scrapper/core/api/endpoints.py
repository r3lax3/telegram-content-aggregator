from typing import List, Literal, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from core.database.uow import UnitOfWork
from core.schemas.post import PostSchema

router = APIRouter(route_class=DishkaRoute)


@router.get("/posts", tags=["posts"], response_model=List[PostSchema])
async def get_posts(
    uow: FromDishka[UnitOfWork],
    channel: str,
    limit: int = 100,
    order: Literal["asc", "desc"] = "desc",
    marked: Optional[Literal["used", "ad"]] = None,
    unmarked: bool = False,
    days_ago: Optional[int] = None,
):
    posts = await uow.posts.get_many_with_params(
        channel_username=channel,
        limit=limit,
        order=order,
        marked=marked,
        unmarked=unmarked,
        created_after=datetime.utcnow() - timedelta(days=days_ago) if days_ago else None,
    )
    return posts
