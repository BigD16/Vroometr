from app.config import settings
from app.documents.runtime import ingestion_service
from app.repositories.document_index import DocumentIndexRepository
from app.services.document_index import DocumentIndexService


def index_service(session):
    return DocumentIndexService(
        DocumentIndexRepository(session),
        ingestion_service(session),
        settings.processing_lease_seconds,
        settings.embedding_model,
        settings.embedding_version,
    )
