import hashlib
from typing import Protocol

import pymupdf

from app.models.attachment import Attachment


class InvalidDocumentFile(ValueError):
    pass


class DocumentContentStorage(Protocol):
    def read_attachment(self, attachment: Attachment) -> bytes: ...


class DocumentInspector(Protocol):
    def inspect(self, attachment: Attachment) -> str: ...


class PdfDocumentInspector:
    """Registration preflight only: no text extraction, OCR, or model calls."""

    def __init__(self, storage: DocumentContentStorage) -> None:
        self._storage = storage

    def inspect(self, attachment: Attachment) -> str:
        content = self._storage.read_attachment(attachment)
        try:
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                if not pdf.is_pdf:
                    raise InvalidDocumentFile("Choose a PDF document.")
                if pdf.needs_pass or pdf.is_encrypted or (pdf.metadata or {}).get("encryption"):
                    raise InvalidDocumentFile(
                        "This PDF is password-protected. Upload an unlocked copy."
                    )
                if pdf.page_count == 0:
                    raise InvalidDocumentFile("The PDF has no pages.")
        except (pymupdf.FileDataError, RuntimeError) as exc:
            raise InvalidDocumentFile("This file could not be read as a PDF.") from exc
        return hashlib.sha256(content).hexdigest()
