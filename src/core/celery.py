from celery import Celery
from celery.schedules import crontab

from core.settings import settings

REDIS_URL = settings.REDIS_URL

celery_app = Celery(
    "aura_stream_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.email_tasks", "tasks.cleanup_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-every-hour": {
        "task": "tasks.cleanup_tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0, hour="*/1"),
    },
}
