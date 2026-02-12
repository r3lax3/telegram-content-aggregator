from fastapi import FastAPI

from .endpoints import router

import logging


# Создаём handler для aiohttp
aiohttp_handler = logging.FileHandler("aiohttp.log", encoding="utf-8")
aiohttp_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
aiohttp_handler.setFormatter(formatter)

# Логгер клиента aiohttp
aiohttp_client_logger = logging.getLogger("aiohttp.client")
aiohttp_client_logger.setLevel(logging.INFO)
aiohttp_client_logger.addHandler(aiohttp_handler)
aiohttp_client_logger.propagate = False  # <-- НЕ отправлять в общий лог

# Логгер сервера aiohttp (если используешь веб-сервер)
aiohttp_server_logger = logging.getLogger("aiohttp.server")
aiohttp_server_logger.setLevel(logging.INFO)
aiohttp_server_logger.addHandler(aiohttp_handler)
aiohttp_server_logger.propagate = False



app = FastAPI(title="Scrapper API")
app.include_router(router)
