from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pymupdf
import pytest
from app.documents.extraction import extract_page
from app.models.attachment_processing import AttachmentProcessing
from app.repositories.document_ingestion import IngestionMessage
from app.services.attachment_processing import ProcessingBusy
from app.services.attachments import AttachmentAccessBlocked
from app.services.document_ingestion import DocumentIngestionService
from app.services.documents import DocumentNotFound, InvalidDocument
from tests.unit.test_documents import META, register, setup_documents


class Jobs:
    def __init__(self):
        self.rows, self.results, self.messages = {}, {}, []

    def get(self, key):
        return self.rows.get(key)

    def pages(self, key):
        return [row for (doc, _), row in self.results.items() if doc == key]

    def save(self, row):
        self.rows[row.document_id] = row
        return row

    def save_page(self, row):
        self.results[row.document_id, row.page_index] = row

    def queue(self, row, user_id):
        self.messages.append(IngestionMessage(user_id, row.document_id, row.attempt_id))
        return self.save(row)


def setup_ingestion():
    owner, other, bike, _, file, attachments, documents, _, service = setup_documents()
    doc = register(service, owner, bike, file).document
    jobs = Jobs()
    ingestion = DocumentIngestionService(jobs, documents, attachments, 300)
    return owner, other, file, doc, service, ingestion, jobs


def test_ingestion_requires_confirmation_and_owner_and_blocks_infection():
    owner, other, file, doc, documents, service, _ = setup_ingestion()
    with pytest.raises(InvalidDocument):
        service.queue(owner.id, doc.id)
    with pytest.raises(DocumentNotFound):
        service.status(other.id, doc.id)
    with pytest.raises(DocumentNotFound):
        service.queue(other.id, doc.id)
    documents.confirm(owner, doc.id, META)
    file.processing = AttachmentProcessing(scan_status="infected")
    with pytest.raises(AttachmentAccessBlocked):
        service.queue(owner.id, doc.id)
    with pytest.raises(AttachmentAccessBlocked):
        service.status(owner.id, doc.id)


def test_attempt_claim_retry_and_stale_results():
    owner, _, _, doc, documents, service, jobs = setup_ingestion()
    documents.confirm(owner, doc.id, META)
    first = service.queue(owner.id, doc.id)
    old = jobs.messages[-1]
    assert service.claim(old) is not None
    assert service.claim(old) is None
    with pytest.raises(ProcessingBusy):
        service.queue(owner.id, doc.id)
    first.retry_after = datetime.now(UTC) - timedelta(seconds=1)
    service.queue(owner.id, doc.id)
    assert not service.finish(old, error_code="late")
    assert not service.start_pages(old, 10)
    current = jobs.messages[-1]
    assert service.claim(current) is not None
    assert service.start_pages(current, 2)
    assert service.finish(current)
    assert first.state == "partial"


def test_extraction_text_blank_and_visual_routing():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((30, 40), "A sample text page with ordinary text.")
        result = extract_page(pdf, 0, uuid4(), "a" * 64)
        assert result.state == "completed" and "sample text" in result.text
        pdf.new_page()
        assert "blank_page" in extract_page(pdf, 1, uuid4(), "a" * 64).visual_score_reasons
        page = pdf.new_page()
        for i in range(12):
            page.draw_line((10, 10 + i * 5), (150, 10 + i * 5))
        page.insert_text((30, 150), "See diagram")
        result = extract_page(pdf, 2, uuid4(), "a" * 64)
        assert result.state == "pending_provider" and result.processing_class == "ocr_vision"
        assert result.vision_version is None and result.ocr_version is None
        assert result.visual_score <= 1


def test_request_dispatches_document_messages_only_after_commit(monkeypatch):
    from app import deps

    events = []

    class Session:
        info = {"ingestion_messages": ["message"]}

        def commit(self):
            events.append("commit")

        def rollback(self):
            events.append("rollback")

        def close(self):
            events.append("close")

    monkeypatch.setattr(deps, "SessionLocal", Session)
    monkeypatch.setattr(deps, "dispatch_committed", lambda messages: None)
    monkeypatch.setattr(deps, "dispatch_ingestion", lambda messages: events.append(messages))
    transaction = deps.get_db()
    next(transaction)
    with pytest.raises(StopIteration):
        next(transaction)
    assert events == ["commit", ["message"], "close"]
    events.clear()
    transaction = deps.get_db()
    next(transaction)
    with pytest.raises(ValueError):
        transaction.throw(ValueError("rollback"))
    assert events == ["rollback", "close"]


def test_worker_document_task_delegates_to_pipeline(monkeypatch):
    from workers import tasks

    called = []
    monkeypatch.setattr(
        tasks.document_pipeline,
        "process",
        lambda *args: called.append(args) or {"status": "completed"},
    )
    assert tasks.process_document.run("user", "doc", "attempt") == {"status": "completed"}
    assert called == [("user", "doc", "attempt")]


def test_image_only_page_is_pending_ocr_with_provenance():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        pixels = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 40, 40), False)
        pixels.clear_with(180)
        page.insert_image(page.rect, pixmap=pixels)
        result = extract_page(pdf, 0, uuid4(), "b" * 64)
        assert result.processing_class == "ocr_enhanced"
        assert result.state == "pending_provider"
        assert result.source_hash == "b" * 64
        assert "large_image_area" in result.visual_score_reasons


def test_page_provenance_rejected_and_stale_page_cannot_overwrite():
    from app.documents.extraction import failed_page

    owner, _, _, doc, documents, service, jobs = setup_ingestion()
    documents.confirm(owner, doc.id, META)
    service.queue(owner.id, doc.id)
    message = jobs.messages[-1]
    service.claim(message)
    service.start_pages(message, 1)
    page = failed_page(0, doc.id, "b" * 64)
    with pytest.raises(InvalidDocument):
        service.save_page(message, page)
    page.source_hash = doc.file_hash
    assert service.save_page(message, page)
    service.finish(message)
    service.queue(owner.id, doc.id)
    assert not service.save_page(message, page)
