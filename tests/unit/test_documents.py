from uuid import uuid4

import pymupdf
import pytest
from app.documents.inspection import InvalidDocumentFile, PdfDocumentInspector
from app.models.attachment import Attachment
from app.models.attachment_processing import AttachmentProcessing
from app.models.bike import Bike
from app.models.user import User
from app.services.attachments import AttachmentAccessBlocked
from app.services.documents import (
    DocumentMetadata,
    DocumentNotFound,
    DocumentService,
    InvalidDocument,
)
from app.services.uploads import AttachmentNotFound
from tests.unit.fakes import InMemoryBikeRepository
from tests.unit.test_uploads import _Attachments


class Documents:
    def __init__(self, bikes):
        self.items = {}
        self.bikes = bikes

    def get(self, document_id, user_id):
        doc = self.items.get(document_id)
        return doc if doc and self.bikes.get(doc.bike_id, user_id) else None

    def list_for_bike(self, bike_id, user_id):
        return [
            doc
            for doc in self.items.values()
            if doc.bike_id == bike_id and self.get(doc.id, user_id)
        ]

    def matching_hash(self, file_hash, user_id):
        return [
            doc
            for doc in self.items.values()
            if doc.file_hash == file_hash and self.get(doc.id, user_id)
        ]

    def add(self, document):
        self.items[document.id] = document
        return document

    save = add

    def clear_primary(self, bike_id):
        for doc in self.items.values():
            if doc.bike_id == bike_id:
                doc.is_primary = False


class Inspector:
    def inspect(self, attachment):
        return "a" * 64


def setup_documents():
    owner, other = User(id=uuid4()), User(id=uuid4())
    bikes = InMemoryBikeRepository()
    bike = bikes.add(Bike(user_id=owner.id))
    foreign = bikes.add(Bike(user_id=other.id))
    attachments = _Attachments()
    file = attachments.add(
        Attachment(id=uuid4(), user_id=owner.id, status="uploaded", mime_type="application/pdf")
    )
    docs = Documents(bikes)
    inspector = Inspector()
    service = DocumentService(docs, attachments, bikes, inspector)
    return owner, other, bike, foreign, file, attachments, docs, inspector, service


META = DocumentMetadata("manufacturer_manual", "Test Make", "Test Model", 2024)


def register(service, owner, bike, file, **kwargs):
    return service.register(owner, bike_id=bike.id, attachment_id=file.id, metadata=META, **kwargs)


def test_primary_confirmation_versions_and_manual_override():
    owner, _, bike, _, file, attachments, _, _, service = setup_documents()
    first = register(service, owner, bike, file).document
    assert first.status == "awaiting_confirmation" and not first.is_primary
    with pytest.raises(InvalidDocument):
        service.select_primary(owner, first.id)
    service.confirm(owner, first.id, META)
    assert first.is_primary
    next_file = attachments.add(
        Attachment(id=uuid4(), user_id=owner.id, status="uploaded", mime_type="application/pdf")
    )
    second = register(service, owner, bike, next_file, supersedes_document_id=first.id).document
    assert first.is_primary and second.revision == 2
    assert second.version_group_id == first.version_group_id
    service.confirm(owner, second.id, META)
    assert second.is_primary and not first.is_primary and first.status == "archived"
    service.select_primary(owner, first.id)
    assert first.is_primary and not second.is_primary
    # Retrying a successful confirmation cannot undo a subsequent manual selection.
    service.confirm(owner, second.id, META)
    assert first.is_primary


def test_duplicate_hash_warns_without_merge_and_is_owner_scoped():
    owner, other, bike, foreign, file, attachments, docs, _, service = setup_documents()
    first = register(service, owner, bike, file).document
    other_file = attachments.add(
        Attachment(id=uuid4(), user_id=owner.id, status="uploaded", mime_type="application/pdf")
    )
    duplicate = register(service, owner, bike, other_file)
    assert duplicate.duplicate_document_ids == [first.id]
    assert duplicate.document.id != first.id and len(docs.items) == 2
    foreign_file = attachments.add(
        Attachment(id=uuid4(), user_id=other.id, status="uploaded", mime_type="application/pdf")
    )
    assert register(service, other, foreign, foreign_file).duplicate_document_ids == []


def test_foreign_references_are_rejected_before_inspecting_files():
    owner, other, bike, foreign, file, _, _, _, service = setup_documents()
    with pytest.raises(DocumentNotFound):
        register(service, owner, foreign, file)
    with pytest.raises(AttachmentNotFound):
        register(service, other, foreign, file)
    first = register(service, owner, bike, file).document
    for operation in [
        lambda: service.confirm(other, first.id, META),
        lambda: service.select_primary(other, first.id),
        lambda: service.list(other, bike.id),
    ]:
        with pytest.raises(DocumentNotFound):
            operation()


def test_confirmation_detects_changed_bytes_and_infected_files():
    owner, _, bike, _, file, _, _, inspector, service = setup_documents()
    draft = register(service, owner, bike, file).document
    inspector.inspect = lambda attachment: "b" * 64
    with pytest.raises(InvalidDocument, match="changed"):
        service.confirm(owner, draft.id, META)
    assert draft.confirmed_at is None
    file.processing = AttachmentProcessing(scan_status="infected")
    with pytest.raises(AttachmentAccessBlocked):
        service.confirm(owner, draft.id, META)


def test_metadata_can_be_corrected_before_confirmation():
    owner, _, bike, _, file, _, _, _, service = setup_documents()
    draft = register(service, owner, bike, file).document
    corrected = DocumentMetadata("supporting_document", "Correct Make", "Correct Model", 2023)
    service.confirm(owner, draft.id, corrected)
    assert draft.make == "Correct Make" and not draft.is_primary
    with pytest.raises(InvalidDocument):
        service.select_primary(owner, draft.id)


def test_inspector_hashes_pdf_and_rejects_passwords_and_malformed_data():
    class Storage:
        content = b""

        def read_attachment(self, attachment):
            return self.content

    storage = Storage()
    inspector = PdfDocumentInspector(storage)
    file = Attachment()
    with pymupdf.open() as pdf:
        pdf.new_page()
        storage.content = pdf.tobytes()
        digest = inspector.inspect(file)
        assert len(digest) == 64 and inspector.inspect(file) == digest
        storage.content = pdf.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="test-owner", user_pw="test-user"
        )
    with pytest.raises(InvalidDocumentFile, match="password-protected"):
        inspector.inspect(file)
    storage.content = b"not a PDF"
    with pytest.raises(InvalidDocumentFile):
        inspector.inspect(file)


def test_primary_selection_rechecks_confirmed_file_bytes():
    owner, _, bike, _, file, _, _, inspector, service = setup_documents()
    document = register(service, owner, bike, file).document
    service.confirm(owner, document.id, META)
    inspector.inspect = lambda attachment: "b" * 64
    with pytest.raises(InvalidDocument, match="changed"):
        service.select_primary(owner, document.id)


def test_newer_confirmed_edition_prevents_confirming_older_draft():
    owner, _, bike, _, file, attachments, _, _, service = setup_documents()
    first = register(service, owner, bike, file).document
    next_file = attachments.add(
        Attachment(id=uuid4(), user_id=owner.id, status="uploaded", mime_type="application/pdf")
    )
    second = register(service, owner, bike, next_file, supersedes_document_id=first.id).document
    service.confirm(owner, second.id, META)
    with pytest.raises(InvalidDocument, match="newer edition"):
        service.confirm(owner, first.id, META)
    assert first.status == "archived" and second.is_primary
