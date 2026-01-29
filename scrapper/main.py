import asyncio
import os
import signal

from core.di import initialize_di_container
from core.logger import get_logger

from core.api.run import run_api
from core.messaging import run_rabbitmq_consumer
from core.workers import run_update_info_worker


logger = get_logger(__name__)

UPDATE_INFO = os.environ.get("UPDATE_INFO")
USE_API = os.environ.get("USE_API")


def main():
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    async def async_main():
        di = initialize_di_container()

        tasks = [asyncio.create_task(run_rabbitmq_consumer(stop_event, di))]

        if USE_API:
            tasks.append(asyncio.create_task(run_api(di)))

        if UPDATE_INFO:
            tasks.append(asyncio.create_task(run_update_info_worker(di.uow)))

        await stop_event.wait()

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    loop.run_until_complete(async_main())


if __name__ == "__main__":
    main()
