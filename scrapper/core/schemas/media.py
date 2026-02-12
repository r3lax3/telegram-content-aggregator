from pydantic import BaseModel

class MediaSchema(BaseModel):
    type: str
    url: str
