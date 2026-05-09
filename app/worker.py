from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "zenvort",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
    worker_max_tasks_per_child=50,
)
