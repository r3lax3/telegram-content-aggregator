from datetime import datetime

from typing import List, Optional
from pydantic import BaseModel


class MediaSchema(BaseModel):
    type: str
    url: str


class PostSchema(BaseModel):
    id: int
    channel_username: str
    mark: Optional[str] = None
    text: Optional[str]
    created_at: datetime
    medias: List[MediaSchema] = []

    class Config:
        from_attributes = True
