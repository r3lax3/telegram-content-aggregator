# core/scrapper/parser.py
import datetime as dt
import re
from typing import List

from bs4 import BeautifulSoup, Tag

from core.dto import MediaSchema, PostSchema
from core.enums import MediaTypeEnum
from core.exceptions import (
    PostIdNotFoundException,
    PostsListNotFoundException,
    VideoUnavailableException,
    MediaUnavailableException,
)


_TGSTAT_LINK_PATTERN = re.compile(
    r'<a\s+href="https?://tgstat\.ru/channel/(@[\w]+)"\s*>\1</a>',
    re.IGNORECASE,
)


def parse_channel_posts(html: str, channel_username: str) -> List[PostSchema]:
    soup = BeautifulSoup(html, "lxml")

    posts_parent_div = soup.find("div", class_="posts-list lm-list-container")
    if not posts_parent_div:
        raise PostsListNotFoundException()

    post_tags = posts_parent_div.find_all(
        "div", class_="card card-body border p-2 px-1 px-sm-3 post-container"
    )

    if not post_tags:
        return []

    parsed_posts = []
    for post_tag in post_tags:
        try:
            post = _parse_single_post(post_tag, channel_username)
            if post:
                parsed_posts.append(post)
        except (VideoUnavailableException, MediaUnavailableException):
            continue
        except Exception:
            continue

    return sorted(parsed_posts, key=lambda p: p.id, reverse=True)


def _parse_single_post(post: Tag, channel_username: str) -> PostSchema | None:
    text = _parse_text(post)
    if not text:
        return None

    post_id = _parse_post_id(post)
    created_at = _parse_created_at(post)
    medias = _parse_medias(post)

    return PostSchema(
        id=post_id,
        channel_username=channel_username,
        text=text,
        created_at=created_at,
        medias=medias,
    )


def _parse_text(post: Tag) -> str:
    post_text_tag = post.select_one(".post-text")
    if not post_text_tag:
        return ""

    html_content = post_text_tag.decode_contents()
    html_content = html_content.replace("<br/>", "\n")

    return _TGSTAT_LINK_PATTERN.sub(r"\1", html_content)


def _parse_post_id(post: Tag) -> int:
    share_element = post.select_one('a[data-src*="/share"]')
    if not share_element or "data-src" not in share_element.attrs:
        raise PostIdNotFoundException()

    share_link = share_element["data-src"]
    if isinstance(share_link, list):
        share_link = share_link[0]

    return int(share_link.split("/")[3])


def _parse_created_at(post: Tag) -> dt.datetime:
    tag_small = post.select_one(".media-body.text-truncate small")
    if not tag_small:
        raise ValueError("не обнаружена дата создания поста")

    text = tag_small.text.strip()

    try:
        return dt.datetime.strptime(text, "%d %b %Y, %H:%M")
    except ValueError:
        created = dt.datetime.strptime(text, "%d %b, %H:%M")
        return created.replace(year=dt.datetime.now().year)


def _parse_medias(post: Tag) -> List[MediaSchema]:
    # проверки на недоступный контент
    unavailable = post.find("div", class_="thumbnail-text")
    if unavailable and "Видео недоступно для предпросмотра" in unavailable.get_text(strip=True):
        raise VideoUnavailableException()

    if post.find("div", class_="carousel-inner"):
        raise MediaUnavailableException()

    medias = []

    # видео
    video_el = post.select_one(".wrapper-video-video source")
    if video_el and video_el.get("src"):
        medias.append(MediaSchema(type=MediaTypeEnum.VIDEO, url=video_el["src"]))  # type: ignore

    # картинка
    img_el = post.select_one("img.post-img-img")
    if img_el and img_el.get("src"):
        medias.append(MediaSchema(type=MediaTypeEnum.IMAGE, url=img_el["src"]))  # type: ignore

    return medias
