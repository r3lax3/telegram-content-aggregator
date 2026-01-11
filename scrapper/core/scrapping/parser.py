import datetime as dt
import re
from typing import List

from bs4 import BeautifulSoup, Tag

from core.enums import MediaTypeEnum
from core.dto import PostSchema, MediaSchema
from core.exceptions import (
    PostIdNotFoundException,
    PostTextNotFoundException,
    PostsListNotFoundException,
    ParsingError,
    VideoUnavailableException,
    MediaUnavailableException,
)
from core.logger import get_logger


logger = get_logger(__name__)


def parse_channel_posts(html: str, channel_username: str) -> List[PostSchema]:
    soup = BeautifulSoup(html, "lxml")

    try:
        posts = _parse_posts_tag_list(soup)
    except (
        PostsListNotFoundException,
        PostTextNotFoundException,
        PostIdNotFoundException,
    ):
        with open(f"error_{channel_username}.html", "w", encoding="utf-8") as f:
            f.write(html)
        raise ParsingError()

    if not posts:
        return []

    parsed_posts = []
    for post in posts:
        try:
            text = _parse_text_from_post(post)
            if not text:
                continue

            created_at = _parse_created_at_from_post(post)
            post_id = _parse_post_id_from_post(post)

            try:
                medias = _parse_medias_from_post(post)
            except (VideoUnavailableException, MediaUnavailableException) as e:
                logger.debug(
                    f"Media parsing error (@{channel_username}/{post_id}) - {e}"
                )
                continue

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            continue

        parsed_posts.append(
            PostSchema(
                id=post_id,
                channel_username=channel_username,
                text=text,
                created_at=created_at,
                medias=medias,
            )
        )

    parsed_posts = sorted(parsed_posts, key=lambda p: p.id, reverse=True)
    return parsed_posts


def _parse_posts_tag_list(soup: BeautifulSoup) -> List[Tag]:
    posts_parent_div = soup.find("div", class_="posts-list lm-list-container")
    if not posts_parent_div:
        raise PostsListNotFoundException()

    posts = posts_parent_div.find_all(
        "div", class_="card card-body border p-2 px-1 px-sm-3 post-container"
    )
    return posts


def _parse_text_from_post(post: Tag) -> str:
    post_text_tag = post.select_one(".post-text")
    if not post_text_tag:
        return ""

    html_content = post_text_tag.decode_contents()

    # Replace <br/> with newlines
    html_content = html_content.replace("<br/>", "\n")

    # Pattern: find <a href="https://tgstat.ru/channel/@username">@username</a>
    tgstat_link_pattern = re.compile(
        r'<a\s+href="https?://tgstat\.ru/channel/(@[\w]+)"\s*>\1</a>',
        re.IGNORECASE,
    )

    # Replace matches with just @username
    cleaned_html = tgstat_link_pattern.sub(r"\1", html_content)

    return cleaned_html


def _parse_created_at_from_post(post: Tag) -> dt.datetime:
    tag_small = post.select_one(".media-body.text-truncate small")
    if not tag_small:
        raise Exception("Post creation date not found")

    formatted_created_at = tag_small.text.strip()
    return _parse_post_datetime(formatted_created_at)


def _parse_post_datetime(created: str) -> dt.datetime:
    try:
        # Format with year: '23 Oct 2024, 13:01'
        created_at = dt.datetime.strptime(created, "%d %b %Y, %H:%M")
        return created_at
    except ValueError:
        # Format without year: '1 Nov, 14:00'
        created_at = dt.datetime.strptime(created, "%d %b, %H:%M")
        now = dt.datetime.now()
        created_at = created_at.replace(year=now.year)
        return created_at


def _parse_post_id_from_post(post: Tag) -> int:
    share_element = post.select_one('a[data-src*="/share"]')
    if share_element and "data-src" in share_element.attrs:
        share_link = share_element["data-src"]

        if isinstance(share_link, list):
            share_link = share_link[0]

        post_id = int(share_link.split("/")[3])
        return post_id
    else:
        raise PostIdNotFoundException()


def _parse_medias_from_post(post: Tag) -> List[MediaSchema]:
    _check_video_unavailable(post)
    _check_carousel(post)

    medias = []

    video = _parse_video(post)
    if video:
        medias.append(video)

    image = _parse_image(post)
    if image:
        medias.append(image)

    return medias


def _check_video_unavailable(post: Tag) -> None:
    unavailable_el = post.find("div", class_="thumbnail-text")
    if unavailable_el and "Видео недоступно для предпросмотра" in unavailable_el.get_text(strip=True):
        raise VideoUnavailableException("Skip: video unavailable for preview")


def _check_carousel(post: Tag) -> None:
    carousel_el = post.find("div", class_="carousel-inner")
    if carousel_el:
        raise MediaUnavailableException("Skip: album")


def _parse_video(post: Tag) -> MediaSchema | None:
    video_element = post.select_one(".wrapper-video-video")
    if not video_element:
        return None

    source_element = video_element.select_one("source")
    if not source_element or "src" not in source_element.attrs:
        return None

    video_url = source_element["src"]
    return MediaSchema(type=MediaTypeEnum.VIDEO.value, url=video_url)


def _parse_image(post: Tag) -> MediaSchema | None:
    image_element = post.select_one("img.post-img-img")
    if image_element:
        image_url = image_element["src"]
        return MediaSchema(type=MediaTypeEnum.IMAGE.value, url=image_url)
    return None
