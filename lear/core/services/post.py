from typing import List

from core.dto import MediaSchema, PostSchema


class PostsService:
    def posts_models_to_schemas(self, posts: List[Post]) -> List[PostSchema]:
        post_schemas = []
        for post in posts:
            post_schema = PostSchema(
                id=post.id,
                created_at=post.created_at,
                channel_username=post.channel_username,
                mark=post.mark,
                text=post.text,
            )
            media_schemas = []
            for media in post.medias:
                media_schema = MediaSchema(
                    post_id=media.post_id,
                    post_channel_username=media.post_channel_username,
                    type=media.type,
                    url=media.url,
                )
                media_schemas.append(media_schema)

            post_schema.medias = media_schemas
            post_schemas.append(post_schema)

        return post_schemas
