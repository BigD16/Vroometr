from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.models.attachment import Attachment
from app.models.attachment_processing import AttachmentProcessing
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ProcessingMessage:
    user_id: UUID
    attachment_id: UUID
    attempt_id: UUID


class ProcessingStore(Protocol):
    def get(self, attachment_id: UUID, user_id: UUID) -> AttachmentProcessing | None: ...

    def save(self, job: AttachmentProcessing) -> AttachmentProcessing: ...

    def queue(self, job: AttachmentProcessing, user_id: UUID) -> AttachmentProcessing: ...


class AttachmentProcessingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, attachment_id: UUID, user_id: UUID) -> AttachmentProcessing | None:
        return self._session.scalars(
            select(AttachmentProcessing)
            .execution_options(populate_existing=True)
            .join(Attachment)
            .where(
                AttachmentProcessing.attachment_id == attachment_id,
                Attachment.user_id == user_id,
            )
        ).first()

    def save(self, job: AttachmentProcessing) -> AttachmentProcessing:
        self._session.add(job)
        self._session.flush()
        return job

    def queue(self, job: AttachmentProcessing, user_id: UUID) -> AttachmentProcessing:
        self.save(job)
        # Request transaction must commit before Celery can observe this attempt.
        self._session.info.setdefault("processing_messages", []).append(
            ProcessingMessage(user_id, job.attachment_id, job.attempt_id),
        )
        return job
