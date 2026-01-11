from pydantic import BaseModel

from .post import PostsService


class ServicesContainer(BaseModel):
    posts: PostsService


def create_services():
    return ServicesContainer(posts=PostsService())
