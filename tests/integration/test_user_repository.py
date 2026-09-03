from collections.abc import Iterator
from datetime import date

import pytest
from app.db import engine
from app.models.user import Entitlement, Role
from app.repositories.parental_consents import ParentalConsentRepository
from app.repositories.users import UserRepository
from app.services.age_gate import AgeGateService, Eligibility
from app.services.users import UserService
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Iterator[Session]:
    try:
        connection = engine.connect()
    except Exception:
        pytest.skip("Postgres is not running")

    transaction = connection.begin()
    exists = connection.execute(text("SELECT to_regclass('public.users')")).scalar()
    if exists is None:
        transaction.rollback()
        connection.close()
        pytest.skip("Run `cd services/api && alembic upgrade head` first")

    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_user_round_trip_in_postgres(db_session: Session) -> None:
    service = UserService(UserRepository(db_session))
    created = service.create("user_clerk_phase1")
    db_session.flush()
    found = service.get_by_clerk_user_id("user_clerk_phase1")
    assert found is not None
    assert found.id == created.id
    assert found.role == Role.USER.value
    assert found.entitlement == Entitlement.NONE.value


def test_parental_consent_round_trip_in_postgres(db_session: Session) -> None:
    exists = db_session.execute(text("SELECT to_regclass('public.parental_consents')")).scalar()
    if exists is None:
        pytest.skip("Run `cd services/api && alembic upgrade head` first")

    users = UserRepository(db_session)
    gate = AgeGateService(users, ParentalConsentRepository(db_session), today=date(2026, 9, 3))
    service = UserService(users)
    user = service.create("user_clerk_consent")
    db_session.flush()
    gate.set_date_of_birth(user, date(2010, 6, 1))
    assert gate.eligibility(user) == Eligibility.NEEDS_CONSENT
    gate.record_granted(
        user,
        guardian_contact="parent@example.com",
        consent_version="2026-09-01",
    )
    db_session.flush()
    assert gate.eligibility(user) == Eligibility.CONSENTED
