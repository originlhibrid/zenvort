from celery import Celery
from worker.config import get_settings

settings = get_settings()

celery_app = Celery(
    "zenvort",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.WORKER_CONCURRENCY,
    task_soft_time_limit=540,
    task_time_limit=600,
)
