import datetime as dt
from typing import List, Optional
from pydantic import BaseModel

from .media import MediaSchema


class PostSchema(BaseModel):
    id: int
    channel_username: str
    mark: Optional[str] = None
    text: Optional[str]
    created_at: dt.datetime
    medias: List[MediaSchema] = []

    class Config:
        from_attributes = True  # ВАЖНО!
