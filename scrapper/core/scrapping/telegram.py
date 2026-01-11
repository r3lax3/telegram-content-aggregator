import os

from telethon import TelegramClient


SESSION_NAME = "tg_acc"
SESSION_FILE_PATH = f"{SESSION_NAME}.session"

API_ID = int(os.environ.get("TELEGRAM_API_ID", "37443963"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "f5092f2f7523d78fb82fbe6ff126bb60")


def get_telegram_client() -> TelegramClient:
    if not os.path.exists(SESSION_FILE_PATH):
        raise FileNotFoundError(f"Session file {SESSION_FILE_PATH} not found!")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    return client
