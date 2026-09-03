from datetime import date

import pytest
from app.services.age_gate import (
    AgeGateService,
    Eligibility,
    InvalidAgeGate,
    UnderageBlocked,
)
from app.services.users import UserService
from tests.unit.fakes import InMemoryParentalConsentRepository, InMemoryUserRepository

_TODAY = date(2026, 9, 3)


def _gate() -> tuple[UserService, AgeGateService]:
    users = InMemoryUserRepository()
    consents = InMemoryParentalConsentRepository()
    return UserService(users), AgeGateService(users, consents, today=_TODAY)


def test_missing_date_of_birth_is_unknown() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_age")
    assert gate.eligibility(user) == Eligibility.UNKNOWN


def test_adult_does_not_need_consent() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_adult")
    gate.set_date_of_birth(user, date(2000, 1, 1))
    assert gate.eligibility(user) == Eligibility.ADULT


def test_teen_needs_then_has_consent() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_teen")
    gate.set_date_of_birth(user, date(2010, 6, 1))
    assert gate.eligibility(user) == Eligibility.NEEDS_CONSENT
    gate.record_granted(
        user,
        guardian_contact="parent@example.com",
        consent_version="2026-09-01",
    )
    assert gate.eligibility(user) == Eligibility.CONSENTED


def test_under_13_is_rejected_and_not_stored() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_kid")
    with pytest.raises(UnderageBlocked):
        gate.set_date_of_birth(user, date(2016, 1, 1))
    assert user.date_of_birth is None
    assert gate.eligibility(user) == Eligibility.UNKNOWN


def test_future_date_of_birth_is_rejected() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_future")
    with pytest.raises(InvalidAgeGate):
        gate.set_date_of_birth(user, date(2027, 1, 1))


def test_blank_consent_fields_are_rejected() -> None:
    users, gate = _gate()
    user = users.create("user_clerk_blank_consent")
    gate.set_date_of_birth(user, date(2010, 6, 1))
    with pytest.raises(InvalidAgeGate):
        gate.record_granted(user, guardian_contact="  ", consent_version="2026-09-01")
    with pytest.raises(InvalidAgeGate):
        gate.record_granted(user, guardian_contact="parent@example.com", consent_version="")
    assert gate.eligibility(user) == Eligibility.NEEDS_CONSENT


def test_thirteenth_birthday_needs_consent_eighteenth_is_adult() -> None:
    users, gate = _gate()
    teen = users.create("user_clerk_just_13")
    gate.set_date_of_birth(teen, date(2013, 9, 3))
    assert gate.eligibility(teen) == Eligibility.NEEDS_CONSENT
    adult = users.create("user_clerk_just_18")
    gate.set_date_of_birth(adult, date(2008, 9, 3))
    assert gate.eligibility(adult) == Eligibility.ADULT
