import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp

from core.enums import MediaType
from core.exceptions import MediaUnavailableError
from core.schemas.media import MediaSchema


logger = logging.getLogger(__name__)


# Media is streamed to disk in small chunks so peak RAM stays at the chunk
# size regardless of how big the file is. Anything over the size cap is
# rejected before it can fill the disk.
DOWNLOAD_CHUNK = 64 * 1024  # bytes read/written per iteration
MAX_MEDIA_BYTES = 20 * 1024 * 1024  # 20 MB hard cap, see fallback policy
DOWNLOAD_TIMEOUT = 60  # seconds per file


class DownloadedMedia:
    """A media item backed by a temporary file on disk."""

    __slots__ = ("type", "path")

    def __init__(self, media_type: MediaType, path: str) -> None:
        self.type = media_type
        self.path = path


@asynccontextmanager
async def downloaded_medias(
    medias: list[MediaSchema],
) -> AsyncIterator[list[DownloadedMedia]]:
    """Download every media of a post to a temp dir, cleaned up on exit.

    Raises MediaUnavailableError if any item fails to download or exceeds the
    size cap, so the caller can skip the whole post.
    """
    tmp_dir = tempfile.mkdtemp(prefix="tg_media_")
    items: list[DownloadedMedia] = []
    try:
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for media in medias:
                path = await _download_to_file(session, media.url, tmp_dir)
                items.append(DownloadedMedia(media.type, path))
        yield items
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _download_to_file(
    session: aiohttp.ClientSession,
    url: str,
    dest_dir: str,
) -> str:
    try:
        async with session.get(url) as resp:
            resp.raise_for_status()

            declared = resp.headers.get("Content-Length")
            if declared is not None and declared.isdigit():
                if int(declared) > MAX_MEDIA_BYTES:
                    raise MediaUnavailableError(
                        f"медиа {int(declared) // (1024 * 1024)} МБ превышает "
                        f"лимит {MAX_MEDIA_BYTES // (1024 * 1024)} МБ: {url}"
                    )

            fd, path = tempfile.mkstemp(dir=dest_dir)
            size = 0
            try:
                with os.fdopen(fd, "wb") as f:
                    async for chunk in resp.content.iter_chunked(DOWNLOAD_CHUNK):
                        size += len(chunk)
                        if size > MAX_MEDIA_BYTES:
                            raise MediaUnavailableError(
                                f"медиа превышает лимит "
                                f"{MAX_MEDIA_BYTES // (1024 * 1024)} МБ: {url}"
                            )
                        f.write(chunk)
            except BaseException:
                os.unlink(path)
                raise

            return path

    except MediaUnavailableError:
        raise
    except (aiohttp.ClientError, OSError) as e:
        raise MediaUnavailableError(f"не удалось скачать медиа {url}: {e}") from e
