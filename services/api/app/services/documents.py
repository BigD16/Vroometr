from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.documents.inspection import DocumentInspector
from app.models.document import Document
from app.models.user import User
from app.repositories.attachments import AttachmentStore
from app.repositories.bikes import BikeStore
from app.repositories.documents import DocumentStore
from app.services.attachments import AttachmentAccessBlocked
from app.services.uploads import AttachmentNotFound, UploadNotComplete


class InvalidDocument(ValueError):
    pass


class DocumentNotFound(LookupError):
    pass


@dataclass(frozen=True)
class DocumentMetadata:
    document_type: str
    make: str
    model: str
    year: int

    def validate(self) -> None:
        if self.document_type not in {"manufacturer_manual", "supporting_document"}:
            raise InvalidDocument("Choose a manufacturer manual or supporting document.")
        if any(
            not isinstance(value, str) or not 1 <= len(value.strip()) <= 100
            for value in (self.make, self.model)
        ):
            raise InvalidDocument("Make and model must contain 1–100 characters.")
        if (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or not 1885 <= self.year <= 2100
        ):
            raise InvalidDocument("Enter a valid model year.")


@dataclass(frozen=True)
class DocumentRegistration:
    document: Document
    duplicate_document_ids: list[UUID]


class DocumentService:
    def __init__(
        self,
        documents: DocumentStore,
        attachments: AttachmentStore,
        bikes: BikeStore,
        inspector: DocumentInspector,
    ) -> None:
        self._documents = documents
        self._attachments = attachments
        self._bikes = bikes
        self._inspector = inspector

    def list(self, user: User, bike_id: UUID) -> list[Document]:
        if self._bikes.get(bike_id, user.id) is None:
            raise DocumentNotFound
        return self._documents.list_for_bike(bike_id, user.id)

    def register(
        self,
        user: User,
        *,
        bike_id: UUID,
        attachment_id: UUID,
        metadata: DocumentMetadata,
        supersedes_document_id: UUID | None = None,
    ) -> DocumentRegistration:
        metadata.validate()
        self._attachments.lock_owner(user.id)
        existing = self.list(user, bike_id)
        attachment = self._attachments.get(attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.status != "uploaded":
            raise UploadNotComplete("Verify the upload before registering a document.")
        if attachment.processing is not None and attachment.processing.scan_status == "infected":
            raise AttachmentAccessBlocked("This file was flagged as infected.")
        if attachment.mime_type != "application/pdf":
            raise InvalidDocument(
                "Document registration currently supports PDFs. Images remain in Files."
            )
        if any(item.attachment_id == attachment_id for item in existing):
            raise InvalidDocument("This file already has a document record for this bike.")
        previous = None
        if supersedes_document_id is not None:
            previous = self._documents.get(supersedes_document_id, user.id)
            if previous is None or previous.bike_id != bike_id:
                raise DocumentNotFound
            if previous.document_type != metadata.document_type:
                raise InvalidDocument("A new edition must have the same document type.")
            if any(
                item.version_group_id == previous.version_group_id
                and item.revision > previous.revision
                for item in existing
            ):
                raise InvalidDocument("Choose the latest edition to create a new version.")
        file_hash = self._inspector.inspect(attachment)
        duplicates = self._documents.matching_hash(file_hash, user.id)
        document = self._documents.add(
            Document(
                id=uuid4(),
                bike_id=bike_id,
                attachment_id=attachment_id,
                document_type=metadata.document_type,
                make=metadata.make.strip(),
                model=metadata.model.strip(),
                year=metadata.year,
                file_hash=file_hash,
                status="awaiting_confirmation",
                is_primary=False,
                version_group_id=previous.version_group_id if previous else uuid4(),
                revision=previous.revision + 1 if previous else 1,
                supersedes_document_id=previous.id if previous else None,
                created_at=datetime.now(UTC),
            )
        )
        return DocumentRegistration(document, [item.id for item in duplicates])

    def confirm(self, user: User, document_id: UUID, metadata: DocumentMetadata) -> Document:
        metadata.validate()
        self._attachments.lock_owner(user.id)
        document = self._documents.get(document_id, user.id)
        if document is None:
            raise DocumentNotFound
        if document.confirmed_at is not None:
            if (document.document_type, document.make, document.model, document.year) == (
                metadata.document_type,
                metadata.make.strip(),
                metadata.model.strip(),
                metadata.year,
            ):
                return document
            raise InvalidDocument(
                "Confirmed metadata is preserved. Register a new edition to change it."
            )
        versions = self._documents.list_for_bike(document.bike_id, user.id)
        if document.document_type != metadata.document_type and any(
            item.id != document.id and item.version_group_id == document.version_group_id
            for item in versions
        ):
            raise InvalidDocument("Versioned documents must keep the same document type.")
        attachment = self._attachments.get(document.attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.processing is not None and attachment.processing.scan_status == "infected":
            raise AttachmentAccessBlocked("This file was flagged as infected.")
        # Recheck the exact bytes before promoting a draft to confirmed status.
        if self._inspector.inspect(attachment) != document.file_hash:
            raise InvalidDocument("The uploaded file changed. Register an unchanged copy instead.")
        if any(
            item.version_group_id == document.version_group_id
            and item.revision > document.revision
            and item.confirmed_at is not None
            for item in versions
        ):
            raise InvalidDocument("A newer edition is already confirmed.")
        for older in versions:
            if (
                older.version_group_id == document.version_group_id
                and older.revision < document.revision
            ):
                older.is_primary = False
                older.status = "archived"
                self._documents.save(older)
        document.make, document.model, document.year = (
            metadata.make.strip(),
            metadata.model.strip(),
            metadata.year,
        )
        document.document_type = metadata.document_type
        document.confirmed_at = datetime.now(UTC)
        document.status = "active"
        if document.document_type == "manufacturer_manual":
            self._documents.clear_primary(document.bike_id)
            document.is_primary = True
        return self._documents.save(document)

    def select_primary(self, user: User, document_id: UUID) -> Document:
        self._attachments.lock_owner(user.id)
        document = self._documents.get(document_id, user.id)
        if document is None:
            raise DocumentNotFound
        if document.document_type != "manufacturer_manual" or document.confirmed_at is None:
            raise InvalidDocument("Confirm a manufacturer manual before selecting it as primary.")
        attachment = self._attachments.get(document.attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.processing is not None and attachment.processing.scan_status == "infected":
            raise AttachmentAccessBlocked("This file was flagged as infected.")
        if self._inspector.inspect(attachment) != document.file_hash:
            raise InvalidDocument("The uploaded file changed. Register an unchanged copy instead.")
        self._documents.clear_primary(document.bike_id)
        document.status = "active"
        document.is_primary = True
        return self._documents.save(document)
