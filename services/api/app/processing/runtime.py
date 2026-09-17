from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.attachment_processing import AttachmentProcessingRepository
from app.repositories.attachments import AttachmentRepository
from app.services.attachment_processing import AttachmentProcessingService


def processing_service(session: Session) -> AttachmentProcessingService:
    return AttachmentProcessingService(
        AttachmentProcessingRepository(session),
        AttachmentRepository(session),
        settings.processing_lease_seconds,
    )
