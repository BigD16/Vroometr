from typing import Protocol
from uuid import UUID

from app.models.maintenance import MaintenanceRecord, MaintenanceRule, TaxonomyGapEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class MaintenanceStore(Protocol):
    def get(self, record_id: UUID) -> MaintenanceRecord | None: ...

    def get_owned(self, record_id: UUID, user_id: UUID) -> MaintenanceRecord | None: ...

    def list_for_bike(self, bike_id: UUID, *, limit: int = 100) -> list[MaintenanceRecord]: ...

    def add(self, record: MaintenanceRecord) -> MaintenanceRecord: ...

    def save(self, record: MaintenanceRecord) -> MaintenanceRecord: ...

    def delete(self, record: MaintenanceRecord) -> None: ...

    def record_taxonomy_gap(
        self,
        *,
        taxonomy_type: str,
        submitted_term: str,
        bike_id: UUID | None,
        mapped_system: str | None,
    ) -> TaxonomyGapEvent: ...

    def list_active_rules(self, bike_id: UUID) -> list[MaintenanceRule]: ...

    def add_rule(self, rule: MaintenanceRule) -> MaintenanceRule: ...

    def get_owned_rule(self, rule_id: UUID, user_id: UUID) -> MaintenanceRule | None: ...

    def delete_rule(self, rule: MaintenanceRule) -> None: ...


class MaintenanceRepository:
    """Persistence for maintenance records. Owner checks join through bikes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, record_id: UUID) -> MaintenanceRecord | None:
        return self._session.get(MaintenanceRecord, record_id)

    def get_owned(self, record_id: UUID, user_id: UUID) -> MaintenanceRecord | None:
        from app.models.bike import Bike

        statement = (
            select(MaintenanceRecord)
            .join(Bike, Bike.id == MaintenanceRecord.bike_id)
            .where(MaintenanceRecord.id == record_id, Bike.user_id == user_id)
        )
        return self._session.scalars(statement).first()

    def list_for_bike(self, bike_id: UUID, *, limit: int = 100) -> list[MaintenanceRecord]:
        statement = (
            select(MaintenanceRecord)
            .where(MaintenanceRecord.bike_id == bike_id)
            .order_by(
                MaintenanceRecord.service_date.desc(),
                MaintenanceRecord.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def add(self, record: MaintenanceRecord) -> MaintenanceRecord:
        self._session.add(record)
        self._session.flush()
        return record

    def save(self, record: MaintenanceRecord) -> MaintenanceRecord:
        self._session.add(record)
        self._session.flush()
        return record

    def delete(self, record: MaintenanceRecord) -> None:
        self._session.delete(record)
        self._session.flush()

    def record_taxonomy_gap(
        self,
        *,
        taxonomy_type: str,
        submitted_term: str,
        bike_id: UUID | None,
        mapped_system: str | None,
    ) -> TaxonomyGapEvent:
        term = submitted_term.strip()[:200]
        statement = select(TaxonomyGapEvent).where(
            TaxonomyGapEvent.taxonomy_type == taxonomy_type,
            func.lower(TaxonomyGapEvent.submitted_term) == term.lower(),
            TaxonomyGapEvent.review_status == "open",
        )
        if mapped_system is None:
            statement = statement.where(TaxonomyGapEvent.mapped_system.is_(None))
        else:
            statement = statement.where(TaxonomyGapEvent.mapped_system == mapped_system)
        existing = self._session.scalars(statement).first()
        if existing is not None:
            existing.occurrence_count += 1
            if bike_id is not None:
                existing.bike_id = bike_id
            self._session.add(existing)
            self._session.flush()
            return existing
        event = TaxonomyGapEvent(
            taxonomy_type=taxonomy_type,
            submitted_term=term,
            bike_id=bike_id,
            mapped_system=mapped_system,
            occurrence_count=1,
            review_status="open",
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_active_rules(self, bike_id: UUID) -> list[MaintenanceRule]:
        statement = (
            select(MaintenanceRule)
            .where(
                MaintenanceRule.bike_id == bike_id,
                MaintenanceRule.active.is_(True),
                MaintenanceRule.validation_status.in_(("active", "validated")),
            )
            .order_by(MaintenanceRule.system, MaintenanceRule.component)
        )
        return list(self._session.scalars(statement).all())

    def add_rule(self, rule: MaintenanceRule) -> MaintenanceRule:
        self._session.add(rule)
        self._session.flush()
        return rule

    def get_owned_rule(self, rule_id: UUID, user_id: UUID) -> MaintenanceRule | None:
        from app.models.bike import Bike

        statement = (
            select(MaintenanceRule)
            .join(Bike, Bike.id == MaintenanceRule.bike_id)
            .where(MaintenanceRule.id == rule_id, Bike.user_id == user_id)
        )
        return self._session.scalars(statement).first()

    def delete_rule(self, rule: MaintenanceRule) -> None:
        self._session.delete(rule)
        self._session.flush()
