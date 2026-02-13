import datetime as dt

from pydantic import BaseModel
from typing import List, Literal, Optional

from .media import MediaSchema


class PostSchema(BaseModel):
    id: int
    channel_username: str
    mark: Optional[Literal["used", "ad"]] = None
    text: Optional[str]
    created_at: dt.datetime
    medias: List[MediaSchema] = []
