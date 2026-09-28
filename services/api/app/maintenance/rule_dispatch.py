"""Queue automatic maintenance-rule extraction after manual page extraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuleExtractionMessage:
    user_id: UUID
    bike_id: UUID
    document_id: UUID
    force: bool = False


def publish(message: RuleExtractionMessage) -> None:
    from workers.celery_app import celery_app

    celery_app.send_task(
        "vroometr.extract_maintenance_rules",
        args=[
            str(message.user_id),
            str(message.bike_id),
            str(message.document_id),
            bool(message.force),
        ],
        retry=False,
    )


def dispatch_rule_extraction(messages, publisher=None) -> None:
    publisher = publisher or publish
    for message in messages:
        try:
            publisher(message)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Rule extraction queue publication failed (%s)", type(exc).__name__
            )
