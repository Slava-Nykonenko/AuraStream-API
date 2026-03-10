from celery import Celery

from core.settings import settings

REDIS_URL = settings.REDIS_URL

celery_app = Celery(
    "aura_stream_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)