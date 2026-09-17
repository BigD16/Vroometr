from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth.tokens import ClerkJwtVerifier, InvalidIdentity, TokenVerifier
from app.auth.webhooks import ClerkWebhookVerifier, WebhookVerifier
from app.config import settings
from app.db import SessionLocal
from app.documents.dispatch import dispatch_ingestion
from app.documents.index_dispatch import dispatch_indexes
from app.errors import AppError
from app.models.user import User
from app.processing.dispatch import dispatch_committed
from app.processing.runtime import processing_service
from app.repositories.attachment_links import AttachmentLinkRepository
from app.repositories.attachments import AttachmentRepository
from app.repositories.bikes import BikeRepository
from app.repositories.parental_consents import ParentalConsentRepository
from app.repositories.users import UserRepository
from app.services.active_bikes import ActiveBikeService
from app.services.age_gate import AgeGateService
from app.services.attachment_links import AttachmentLinkService
from app.services.attachment_processing import AttachmentProcessingService
from app.services.attachments import AttachmentService
from app.services.bikes import BikeService
from app.services.storage_quota import StorageQuotaService
from app.services.uploads import ObjectStorage, UploadService
from app.services.users import UserService
from app.storage.s3 import S3ObjectStorage


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
        dispatch_committed(session.info.pop("processing_messages", []))
        dispatch_ingestion(session.info.pop("ingestion_messages", []))
        dispatch_indexes(session.info.pop("index_messages", []))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifier:
    return ClerkJwtVerifier(settings.clerk_jwks_url, settings.clerk_authorized_party)


@lru_cache(maxsize=1)
def get_clerk_webhook_verifier() -> WebhookVerifier:
    return ClerkWebhookVerifier(settings.clerk_webhook_secret)


def get_user_service(session: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(session))


def get_age_gate_service(session: Session = Depends(get_db)) -> AgeGateService:
    return AgeGateService(UserRepository(session), ParentalConsentRepository(session))


def get_bike_service(session: Session = Depends(get_db)) -> BikeService:
    return BikeService(BikeRepository(session))


def get_active_bike_service(session: Session = Depends(get_db)) -> ActiveBikeService:
    return ActiveBikeService(UserRepository(session), BikeRepository(session))


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage(
        bucket=settings.s3_bucket,
        region=settings.aws_default_region,
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url.strip() or None,
    )


def get_upload_service(
    session: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> UploadService:
    return UploadService(AttachmentRepository(session), storage, processing_service(session))


def require_clerk_user_id(
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise AppError("unauthenticated", "Sign in required", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError("unauthenticated", "Sign in required", status_code=401)
    try:
        return verifier.clerk_user_id(token)
    except InvalidIdentity as exc:
        raise AppError("unauthenticated", "Sign in required", status_code=401) from exc


def get_current_user(
    clerk_user_id: Annotated[str, Depends(require_clerk_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return user_service.ensure(clerk_user_id)


def get_attachment_link_service(session: Session = Depends(get_db)) -> AttachmentLinkService:
    return AttachmentLinkService(
        AttachmentLinkRepository(session), AttachmentRepository(session), BikeRepository(session),
    )


def get_attachment_service(
    session: Session = Depends(get_db), storage: S3ObjectStorage = Depends(get_object_storage),
) -> AttachmentService:
    return AttachmentService(
        AttachmentRepository(session), AttachmentLinkRepository(session),
        BikeRepository(session), storage,
    )


def get_storage_quota_service(session: Session = Depends(get_db)) -> StorageQuotaService:
    return StorageQuotaService(AttachmentRepository(session))


def get_attachment_processing_service(
    session: Session = Depends(get_db),
) -> AttachmentProcessingService:
    return processing_service(session)


def get_document_service(
    session: Session = Depends(get_db), storage: S3ObjectStorage = Depends(get_object_storage),
):
    from app.documents.inspection import PdfDocumentInspector
    from app.repositories.documents import DocumentRepository
    from app.services.documents import DocumentService

    return DocumentService(DocumentRepository(session), AttachmentRepository(session),
                           BikeRepository(session), PdfDocumentInspector(storage))


def get_conversation_service(session: Session = Depends(get_db)):
    from app.repositories.conversations import ConversationRepository
    from app.services.conversations import ConversationService

    return ConversationService(ConversationRepository(session), BikeRepository(session))
