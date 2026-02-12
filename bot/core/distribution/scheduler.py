import logging

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dishka import AsyncContainer

from .distributor import distribute_posts_globally


logger = logging.getLogger(__name__)


def _format_timedelta(td) -> str:
    if td is None or td.total_seconds() < 0:
        return "неизвестно"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} ч.")
    if minutes:
        parts.append(f"{minutes} мин.")
    return " ".join(parts) if parts else "меньше минуты"


def _get_human_next_run_info(job, now: datetime) -> str:
    next_run = job.next_run_time
    if not next_run:
        return "неизвестно (возможно, уже отработал сегодня)"

    delta = next_run - now
    if delta.total_seconds() < 0:
        from dateutil.relativedelta import relativedelta
        next_run = next_run + relativedelta(days=1)
        delta = next_run - now

    time_str = next_run.strftime("%Y-%m-%d %H:%M:%S %Z")
    human_delta = _format_timedelta(delta)
    return f"через {human_delta} ({time_str})"


class DistributionScheduler:
    def __init__(self, container: AsyncContainer):
        self._container = container
        self._scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    def start(self) -> None:
        self._scheduler.start()
        now = datetime.now(self._scheduler.timezone)

        try:
            for hour in (8, 12, 16, 20):
                self._add_job(hour, now)

            logger.info("Планировщик успешно запущен")

        except Exception as e:
            logger.warning(f"Планировщик не запущен: {e}")

    def _add_job(self, hour: int, now: datetime) -> None:
        job_id = f"distribute_posts_{hour}h"

        job = self._scheduler.add_job(
            distribute_posts_globally,
            trigger=CronTrigger(
                hour=hour, minute=0,
                timezone=self._scheduler.timezone,
            ),
            kwargs={"container": self._container},
            id=job_id
        )

        next_run_info = _get_human_next_run_info(job, now)
        logger.info(f"Создан джоб {job_id}: следующий запуск {next_run_info}")
