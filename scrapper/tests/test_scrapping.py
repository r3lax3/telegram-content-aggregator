import asyncio
import datetime as dt

import aiohttp
import pytest

from core.enums import MediaTypeEnum
from core.scrapper.parser import parse_channel_posts
from core.scrapper.service import CHANNEL_URL_TEMPLATE, USER_AGENT


PHOTO_GROUP_HTML = """
<div class="tgme_widget_message js-widget_message" data-post="abakan_smi/20095">
  <a class="tgme_widget_message_photo_wrap grouped_media_wrap js-message_photo"
     style="background-image: url('https://cdn4.telesco.pe/file/photo1.jpg');"></a>
  <a class="tgme_widget_message_photo_wrap grouped_media_wrap js-message_photo"
     style="background-image: url('https://cdn4.telesco.pe/file/photo2.jpg');"></a>
  <div class="tgme_widget_message_text js-message_text" dir="auto">
    <tg-emoji emoji-id="1"><i class="emoji"><b>❗️</b></i></tg-emoji>
    <b>Заголовок</b><br><br>Текст поста.
  </div>
  <time datetime="2026-04-27T08:15:07+00:00"></time>
</div>
"""

SINGLE_VIDEO_HTML = """
<div class="tgme_widget_message js-widget_message" data-post="abakan_smi/20077">
  <a class="tgme_widget_message_video_player js-message_video_player">
    <video src="https://cdn4.telesco.pe/file/video.mp4"></video>
  </a>
  <div class="tgme_widget_message_text js-message_text" dir="auto">
    <b>Видео-новость</b><br>описание
  </div>
  <time datetime="2026-04-26T15:01:10+00:00"></time>
</div>
"""

SINGLE_PHOTO_HTML = """
<div class="tgme_widget_message js-widget_message" data-post="abakan_smi/20100">
  <a class="tgme_widget_message_photo_wrap js-message_photo"
     style="background-image:url('https://cdn4.telesco.pe/file/single.jpg')"></a>
  <div class="tgme_widget_message_text js-message_text" dir="auto">текст</div>
  <time datetime="2026-04-27T10:00:00+00:00"></time>
</div>
"""

NO_DATA_POST_HTML = """
<div class="tgme_widget_message_service_date_wrap">
  <div class="tgme_widget_message_service_date">April 27</div>
</div>
"""


def test_parse_photo_group_skips_media():
    posts = parse_channel_posts(PHOTO_GROUP_HTML, "abakan_smi")
    assert len(posts) == 1

    post = posts[0]
    assert post.id == 20095
    assert post.channel_username == "abakan_smi"
    assert post.medias == []
    assert "<b>Заголовок</b>" in post.text
    assert "\n\nТекст поста." in post.text
    assert "❗️" in post.text
    assert post.created_at == dt.datetime(2026, 4, 27, 8, 15, 7)


def test_parse_single_video_keeps_media():
    posts = parse_channel_posts(SINGLE_VIDEO_HTML, "abakan_smi")
    assert len(posts) == 1

    post = posts[0]
    assert post.id == 20077
    assert len(post.medias) == 1
    assert post.medias[0].type == MediaTypeEnum.VIDEO
    assert post.medias[0].url == "https://cdn4.telesco.pe/file/video.mp4"
    assert "<b>Видео-новость</b>" in post.text


def test_parse_single_photo_keeps_media():
    posts = parse_channel_posts(SINGLE_PHOTO_HTML, "abakan_smi")
    assert len(posts) == 1

    post = posts[0]
    assert post.id == 20100
    assert len(post.medias) == 1
    assert post.medias[0].type == MediaTypeEnum.IMAGE
    assert post.medias[0].url == "https://cdn4.telesco.pe/file/single.jpg"


def test_service_date_blocks_are_ignored():
    posts = parse_channel_posts(NO_DATA_POST_HTML, "abakan_smi")
    assert posts == []


def test_posts_sorted_by_id_desc():
    html = SINGLE_PHOTO_HTML + SINGLE_VIDEO_HTML
    posts = parse_channel_posts(html, "abakan_smi")
    assert [p.id for p in posts] == [20100, 20077]


@pytest.mark.asyncio
async def test_fetch_real_channel_returns_posts():
    """Smoke test against the live t.me/s preview. Skipped if network is unavailable."""
    url = CHANNEL_URL_TEMPLATE.format(username="durov")
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                if resp.status != 200:
                    pytest.skip(f"t.me returned HTTP {resp.status}")
                html = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        pytest.skip(f"network unavailable: {e}")

    posts = parse_channel_posts(html, "durov")
    assert posts, "expected at least one post in the live preview"
    assert all(p.channel_username == "durov" for p in posts)
