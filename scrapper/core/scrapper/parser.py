import datetime as dt
import re
from typing import List

from bs4 import BeautifulSoup, Tag

from core.dto import MediaSchema, PostSchema
from core.enums import MediaTypeEnum


_BG_IMAGE_RE = re.compile(
    r"background-image\s*:\s*url\(['\"]?([^'\")]+)['\"]?\)",
    re.IGNORECASE,
)
_ALLOWED_TAG_ATTRS = {
    "a": {"href"},
    "b": set(),
    "strong": set(),
    "i": set(),
    "em": set(),
    "u": set(),
    "s": set(),
    "tg-emoji": {"emoji-id"},
    "code": set(),
    "pre": set(),
    "blockquote": set(),
}
_UNWRAP_TAGS = ("picture", "source", "canvas", "video", "img", "span", "div")


def parse_channel_posts(html: str, channel_username: str) -> List[PostSchema]:
    soup = BeautifulSoup(html, "lxml")

    message_tags = soup.select("div.tgme_widget_message[data-post]")
    if not message_tags:
        return []

    posts: List[PostSchema] = []
    for tag in message_tags:
        try:
            post = _parse_single_post(tag, channel_username)
        except Exception:
            continue
        if post:
            posts.append(post)

    return sorted(posts, key=lambda p: p.id, reverse=True)


def _parse_single_post(post: Tag, channel_username: str) -> PostSchema | None:
    post_id = _parse_post_id(post)
    if post_id is None:
        return None

    text = _parse_text(post)
    medias = _parse_medias(post)

    if not text and not medias:
        return None

    return PostSchema(
        id=post_id,
        channel_username=channel_username,
        text=text,
        created_at=_parse_created_at(post),
        medias=medias,
    )


def _parse_post_id(post: Tag) -> int | None:
    data_post = post.get("data-post")
    if not data_post or "/" not in data_post:
        return None
    _, _, post_id_str = data_post.partition("/")
    if not post_id_str.isdigit():
        return None
    return int(post_id_str)


def _parse_created_at(post: Tag) -> dt.datetime:
    time_el = post.select_one("time[datetime]")
    if not time_el or not time_el.get("datetime"):
        return dt.datetime.utcnow()

    parsed = dt.datetime.fromisoformat(time_el["datetime"])
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_text(post: Tag) -> str:
    text_tag = post.select_one(".tgme_widget_message_text")
    if not text_tag:
        return ""

    fragment = BeautifulSoup(str(text_tag), "lxml")
    container = fragment.select_one(".tgme_widget_message_text")
    if not container:
        return ""

    for emoji in container.find_all("tg-emoji"):
        emoji_char = ""
        emoji_i = emoji.find("i", class_="emoji")
        if emoji_i:
            emoji_char = emoji_i.get_text(strip=True)
        if not emoji_char:
            emoji_char = emoji.get_text(strip=True)
        emoji.clear()
        if emoji_char:
            emoji.append(emoji_char)

    for br in container.find_all("br"):
        br.replace_with("\n")

    for tag_name in _UNWRAP_TAGS:
        for el in list(container.find_all(tag_name)):
            el.unwrap()

    for el in container.find_all(True):
        allowed = _ALLOWED_TAG_ATTRS.get(el.name)
        if allowed is None:
            el.unwrap()
            continue
        el.attrs = {k: v for k, v in el.attrs.items() if k in allowed}

    return container.decode_contents().strip()


def _parse_medias(post: Tag) -> List[MediaSchema]:
    photo_wraps = post.select(".tgme_widget_message_photo_wrap")
    video_players = post.select(".tgme_widget_message_video_player")

    if len(photo_wraps) + len(video_players) != 1:
        return []

    if video_players:
        video_el = video_players[0].select_one("video[src]")
        if video_el and video_el.get("src"):
            return [MediaSchema(type=MediaTypeEnum.VIDEO, url=video_el["src"])]
        return []

    style = photo_wraps[0].get("style", "")
    match = _BG_IMAGE_RE.search(style)
    if match:
        return [MediaSchema(type=MediaTypeEnum.IMAGE, url=match.group(1))]
    return []
