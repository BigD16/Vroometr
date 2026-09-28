"""Extract and activate maintenance rules from a manufacturer manual's pages."""

from __future__ import annotations

import logging
from uuid import UUID

from app.db import SessionLocal
from app.maintenance.rule_extraction import PIPELINE_VERSION
from app.repositories.bikes import BikeRepository
from app.repositories.document_ingestion import DocumentIngestionRepository
from app.repositories.documents import DocumentRepository
from app.repositories.maintenance import MaintenanceRepository
from app.repositories.users import UserRepository
from app.services.maintenance import InvalidMaintenance, MaintenanceService

from vroometr.ai.factory import get_chat_model
from vroometr.ai.unconfigured import UnconfiguredError

logger = logging.getLogger(__name__)


def process(
    user_id: str,
    bike_id: str,
    document_id: str,
    force: bool = False,
    *,
    chat=None,
) -> dict:
    """Load completed pages → propose → validate → activate. Soft-fails on config gaps."""
    uid, bid, did = UUID(user_id), UUID(bike_id), UUID(document_id)
    try:
        with SessionLocal.begin() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                return {"status": "ignored", "reason": "user_missing"}
            document = DocumentRepository(session).get(did, uid)
            if (
                document is None
                or document.bike_id != bid
                or document.document_type != "manufacturer_manual"
                or document.status != "active"
                or document.confirmed_at is None
            ):
                return {"status": "ignored", "reason": "document_not_eligible"}

            service = MaintenanceService(
                MaintenanceRepository(session), BikeRepository(session)
            )
            pages = DocumentIngestionRepository(session).pages(did)
            result = service.extract_from_document(
                user,
                bike_id=bid,
                document_id=did,
                pages=pages,
                chat=chat or get_chat_model(),
                activate=True,
                force=force,
            )
            return {
                "status": "skipped" if result.get("skipped") else "ok",
                "pipeline_version": result.get("pipeline_version", PIPELINE_VERSION),
                "accepted": len(result.get("accepted") or []),
                "rejected": len(result.get("rejected") or []),
                "reason": result.get("reason"),
            }
    except UnconfiguredError:
        logger.warning("Rule extraction skipped: chat model unconfigured")
        return {"status": "skipped", "reason": "chat_unconfigured"}
    except InvalidMaintenance as exc:
        logger.warning("Rule extraction invalid: %s", exc)
        return {"status": "failed", "reason": "invalid"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Rule extraction failed (%s)", type(exc).__name__)
        return {"status": "failed", "reason": type(exc).__name__}
