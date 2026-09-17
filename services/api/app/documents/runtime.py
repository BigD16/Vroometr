from app.config import settings
from app.repositories.attachments import AttachmentRepository
from app.repositories.document_ingestion import DocumentIngestionRepository
from app.repositories.documents import DocumentRepository
from app.services.document_ingestion import DocumentIngestionService
from app.storage.s3 import S3ObjectStorage


def ingestion_service(session):
    return DocumentIngestionService(
        DocumentIngestionRepository(session),
        DocumentRepository(session),
        AttachmentRepository(session),
        settings.processing_lease_seconds,
    )


def document_storage():
    return S3ObjectStorage(
        bucket=settings.s3_bucket,
        region=settings.aws_default_region,
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url.strip() or None,
    )
