"""Run an attachment check with durable claims and fenced completion."""

import logging
from uuid import UUID

from app.db import SessionLocal
from app.processing.runtime import processing_service
from app.repositories.attachment_processing import ProcessingMessage
from app.scanning.ports import MalwareScanner, ScanResult, UnconfiguredScanner

logger = logging.getLogger(__name__)


def process(
    user_id: str,
    attachment_id: str,
    attempt_id: str,
    *,
    scanner: MalwareScanner | None = None,
) -> dict[str, str]:
    message = ProcessingMessage(UUID(user_id), UUID(attachment_id), UUID(attempt_id))
    with SessionLocal.begin() as session:
        claim = processing_service(session).claim(message)
    if claim is None:
        return {"status": "ignored"}

    # No DB lock is held while external scanning executes.
    scanner = scanner or UnconfiguredScanner()
    result = None
    error_code = None
    try:
        result = scanner.scan(claim.object_key)
        if not isinstance(result, ScanResult):
            result = None
            raise ValueError("Scanner returned an invalid result")
    except Exception as exc:
        error_code = "scanner_failed"
        logger.error(
            "Attachment scanner failed",
            extra={
                "attachment_id": attachment_id,
                "error_type": type(exc).__name__,
            },
        )
    with SessionLocal.begin() as session:
        applied = processing_service(session).finish(message, result=result, error_code=error_code)
    return {"status": ("failed" if error_code else "completed") if applied else "ignored"}
