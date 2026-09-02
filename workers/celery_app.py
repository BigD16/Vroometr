from celery import Celery

from vroometr.settings import settings

celery_app = Celery(
    "vroometr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.tasks"],
)
