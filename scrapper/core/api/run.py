import uvicorn

from core.api.app import app


async def run_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=5000, loop="asyncio")
    server = uvicorn.Server(config)

    await server.serve()
