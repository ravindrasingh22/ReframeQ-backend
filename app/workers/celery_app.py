from celery import Celery

from app.core.config import settings

celery_app = Celery('reframeq', broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task
def example_health_task() -> str:
    return 'ok'
