import logging
from typing import Protocol

from app.db import SessionLocal
from app.processing.runtime import processing_service
from app.repositories.attachment_processing import ProcessingMessage

logger = logging.getLogger(__name__)


class ProcessingPublisher(Protocol):
    def publish(self, message: ProcessingMessage) -> None: ...


class CeleryProcessingPublisher:
    def publish(self, message: ProcessingMessage) -> None:
        from workers.celery_app import celery_app

        celery_app.send_task(
            "vroometr.process_attachment",
            args=[str(message.user_id), str(message.attachment_id), str(message.attempt_id)],
            retry=False,
        )


def dispatch_committed(
    messages: list[ProcessingMessage],
    publisher: ProcessingPublisher | None = None,
) -> None:
    """Called only after commit. DB state remains retryable if publishing is interrupted."""
    publisher = publisher or CeleryProcessingPublisher()
    for message in messages:
        try:
            publisher.publish(message)
        except Exception as exc:
            logger.error(
                "Attachment queue publication failed (%s)",
                type(exc).__name__,
                extra={
                    "attachment_id": str(message.attachment_id),
                    "error_type": type(exc).__name__,
                },
            )
            try:
                with SessionLocal.begin() as session:
                    processing_service(session).finish(
                        message,
                        error_code="queue_unavailable",
                        queued_failure=True,
                    )
            except Exception as persist_exc:
                # The committed queued row survives and can be retried after its lease.
                logger.error(
                    "Could not persist attachment queue failure",
                    extra={
                        "attachment_id": str(message.attachment_id),
                        "error_type": type(persist_exc).__name__,
                    },
                )
