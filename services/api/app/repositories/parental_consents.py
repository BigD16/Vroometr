from typing import Protocol
from uuid import UUID

from app.models.parental_consent import ParentalConsent
from sqlalchemy import select
from sqlalchemy.orm import Session


class ParentalConsentStore(Protocol):
    def add(self, consent: ParentalConsent) -> ParentalConsent: ...

    def latest_for_minor(self, minor_user_id: UUID) -> ParentalConsent | None: ...


class ParentalConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, consent: ParentalConsent) -> ParentalConsent:
        self._session.add(consent)
        self._session.flush()
        return consent

    def latest_for_minor(self, minor_user_id: UUID) -> ParentalConsent | None:
        statement = (
            select(ParentalConsent)
            .where(ParentalConsent.minor_user_id == minor_user_id)
            .order_by(ParentalConsent.created_at.desc())
        )
        return self._session.scalars(statement).first()
