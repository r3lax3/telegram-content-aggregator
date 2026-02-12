from pydantic import BaseModel
from typing import Literal


class MediaSchema(BaseModel):
    type: Literal["image", "video"]
    url: str
