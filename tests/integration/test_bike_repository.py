from collections.abc import Iterator
from datetime import date

import pytest
from app.db import engine
from app.repositories.bikes import BikeRepository
from app.repositories.users import UserRepository
from app.services.bikes import BikeNotFound, BikePatch, BikeService
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
    exists = connection.execute(text("SELECT to_regclass('public.bikes')")).scalar()
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


def test_bike_round_trip_is_owner_scoped_in_postgres(db_session: Session) -> None:
    users = UserRepository(db_session)
    bikes = BikeService(BikeRepository(db_session), today=date(2026, 9, 3))
    service = UserService(users)
    owner = service.create("user_clerk_bike_owner")
    other = service.create("user_clerk_bike_other")
    db_session.flush()
    created = bikes.create(
        owner,
        nickname="YZ",
        make="Yamaha",
        model="YZ250",
        year=2006,
        displacement=250,
        bike_type="dirt_bike",
        stroke_type="2T",
        current_engine_hours=42.7,
        current_engine_hours_is_estimated=False,
    )
    db_session.flush()
    found = bikes.get(owner, created.id)
    assert found.nickname == "YZ"
    assert found.user_id == owner.id
    assert [bike.id for bike in bikes.list_for_user(owner)] == [created.id]
    with pytest.raises(BikeNotFound):
        bikes.get(other, created.id)
    archived = bikes.update(owner, created.id, BikePatch(status="archive"))
    db_session.flush()
    assert archived.status == "archive"
