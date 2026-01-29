from fastapi import FastAPI
from .endpoints import router
import logging


# Set levels for specific loggers
logging.getLogger("aiohttp.client").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce noise

app = FastAPI(title="Scrapper API")
app.include_router(router)
