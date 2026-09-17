from pipelines import attachment_processing as attachment_pipeline
from pipelines import document_index as index_pipeline
from pipelines import document_pipeline
from pipelines import health as health_pipeline

from workers.celery_app import celery_app


@celery_app.task(name="vroometr.health")
def health() -> dict:
    return health_pipeline.process()


@celery_app.task(name="vroometr.process_attachment")
def process_attachment(user_id: str, attachment_id: str, attempt_id: str) -> dict:
    return attachment_pipeline.process(user_id, attachment_id, attempt_id)


@celery_app.task(name="vroometr.process_document")
def process_document(user_id: str, document_id: str, attempt_id: str) -> dict:
    return document_pipeline.process(user_id, document_id, attempt_id)


@celery_app.task(name="vroometr.index_document")
def index_document(user_id: str, document_id: str, attempt_id: str) -> dict:
    return index_pipeline.process(user_id, document_id, attempt_id)
