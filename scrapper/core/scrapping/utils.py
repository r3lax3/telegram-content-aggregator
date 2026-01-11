import os

from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserType, BrowserContext


PROXY_SERVER = os.environ.get("PROXY_SERVER")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")


async def get_context(browser: Browser) -> BrowserContext:
    return await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
    )


async def get_browser(p: BrowserType) -> Browser:
    proxy_config = None
    if PROXY_SERVER:
        proxy_config = {
            "server": PROXY_SERVER,
            "username": PROXY_USERNAME,
            "password": PROXY_PASSWORD,
        }

    return await p.chromium.launch(
        headless=False,
        proxy=proxy_config,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )


def log_html(html: str, file_path: str) -> None:
    soup = BeautifulSoup(html, "lxml")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
