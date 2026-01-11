import uvicorn

from core.di import DependencyInjector


async def run_api(di: DependencyInjector):
    config = uvicorn.Config(di.app, host="0.0.0.0", port=5000, loop="asyncio")
    server = uvicorn.Server(config)

    await server.serve()
