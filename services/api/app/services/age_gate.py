from datetime import UTC, date, datetime
from enum import StrEnum

from app.models.parental_consent import ConsentStatus, ParentalConsent
from app.models.user import User
from app.repositories.parental_consents import ParentalConsentStore
from app.repositories.users import UserStore


class Eligibility(StrEnum):
    UNKNOWN = "unknown"
    ADULT = "adult"
    NEEDS_CONSENT = "needs_consent"
    CONSENTED = "consented"
    BLOCKED_UNDER_13 = "blocked_under_13"


class InvalidAgeGate(ValueError):
    """Date of birth or guardian consent input is not usable."""


class UnderageBlocked(ValueError):
    """Under-13 accounts are not permitted."""


def years_old(born: date, today: date) -> int:
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return years


class AgeGateService:
    """18+ may use Vroometr directly. Ages 13–17 need a granted, versioned consent."""

    def __init__(
        self,
        users: UserStore,
        consents: ParentalConsentStore,
        *,
        today: date | None = None,
    ) -> None:
        self._users = users
        self._consents = consents
        self._today = today

    def _today_utc(self) -> date:
        return self._today or datetime.now(UTC).date()

    def eligibility(self, user: User) -> Eligibility:
        if user.date_of_birth is None:
            return Eligibility.UNKNOWN
        age = years_old(user.date_of_birth, self._today_utc())
        if age < 13:
            return Eligibility.BLOCKED_UNDER_13
        if age >= 18:
            return Eligibility.ADULT
        latest = self._consents.latest_for_minor(user.id)
        if latest is not None and latest.status == ConsentStatus.GRANTED.value:
            return Eligibility.CONSENTED
        return Eligibility.NEEDS_CONSENT

    def set_date_of_birth(self, user: User, date_of_birth: date) -> User:
        today = self._today_utc()
        if date_of_birth > today:
            raise InvalidAgeGate("date_of_birth cannot be in the future")
        if years_old(date_of_birth, today) < 13:
            raise UnderageBlocked("Vroometr does not allow accounts under 13")
        user.date_of_birth = date_of_birth
        user.updated_at = datetime.now(UTC)
        return self._users.save(user)

    def record_granted(
        self,
        minor: User,
        *,
        guardian_contact: str,
        consent_version: str,
    ) -> ParentalConsent:
        guardian_contact = guardian_contact.strip()
        consent_version = consent_version.strip()
        if not guardian_contact:
            raise InvalidAgeGate("guardian_contact is required")
        if not consent_version:
            raise InvalidAgeGate("consent_version is required")
        if self.eligibility(minor) == Eligibility.BLOCKED_UNDER_13:
            raise UnderageBlocked("Vroometr does not allow accounts under 13")
        now = datetime.now(UTC)
        consent = ParentalConsent(
            minor_user_id=minor.id,
            guardian_contact=guardian_contact,
            consent_version=consent_version,
            status=ConsentStatus.GRANTED.value,
            accepted_at=now,
            created_at=now,
            updated_at=now,
        )
        return self._consents.add(consent)
