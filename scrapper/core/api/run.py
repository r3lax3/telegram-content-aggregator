import uvicorn
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka

from core.api.app import app


async def run_api(dishka: AsyncContainer):
    setup_dishka(dishka, app)

    config = uvicorn.Config(app, host="0.0.0.0", port=5000, loop="asyncio")
    server = uvicorn.Server(config)

    await server.serve()
