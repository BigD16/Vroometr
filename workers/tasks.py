from pipelines import health as health_pipeline

from workers.celery_app import celery_app


@celery_app.task(name="vroometr.health")
def health() -> dict:
    return health_pipeline.process()
