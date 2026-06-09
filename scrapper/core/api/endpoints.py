from typing import List, Literal

from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from core.dto import PostSchema
from core.scrapper.service import ScrapperService
from core.exceptions import ChannelNotFound, ScrappingError

router = APIRouter(route_class=DishkaRoute)


@router.get("/posts", tags=["posts"], response_model=List[PostSchema])
async def get_posts(
    service: FromDishka[ScrapperService],
    channel: str,
    limit: int = 20,
    order: Literal["asc", "desc"] = "desc",
):
    """Fetch a donor channel's latest posts in real time.

    Posts are scraped on every request, so media URLs are fresh and usable
    by the caller immediately.
    """
    try:
        return await service.fetch_posts(channel, limit=limit, order=order)
    except ChannelNotFound:
        raise HTTPException(status_code=404, detail=f"Channel @{channel} not found")
    except ScrappingError as e:
        raise HTTPException(status_code=502, detail=str(e))
