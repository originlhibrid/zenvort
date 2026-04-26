from celery import Celery
from api.config import get_settings

settings = get_settings()

celery_app = Celery("zenvort-api", broker=settings.REDIS_URL)
