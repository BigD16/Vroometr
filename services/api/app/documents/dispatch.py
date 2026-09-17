import logging

from app.db import SessionLocal
from app.documents.runtime import ingestion_service

logger = logging.getLogger(__name__)


def publish(message):
    from workers.celery_app import celery_app

    celery_app.send_task(
        "vroometr.process_document",
        args=[str(message.user_id), str(message.document_id), str(message.attempt_id)],
        retry=False,
    )


def dispatch_ingestion(messages, publisher=None):
    publisher = publisher or publish
    for message in messages:
        try:
            publisher(message)
        except Exception as exc:
            logger.error("Document queue publication failed (%s)", type(exc).__name__)
            try:
                with SessionLocal.begin() as session:
                    ingestion_service(session).finish(
                        message, error_code="queue_unavailable", queued_failure=True
                    )
            except Exception as persist_exc:
                logger.error(
                    "Could not persist document queue failure (%s)", type(persist_exc).__name__
                )
