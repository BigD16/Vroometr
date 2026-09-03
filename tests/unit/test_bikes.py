from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.services.bikes import BikeNotFound, BikeService, InvalidBike
from app.services.users import UserService
from tests.unit.fakes import InMemoryBikeRepository, InMemoryUserRepository

_TODAY = date(2026, 9, 3)


def _services() -> tuple[UserService, BikeService]:
    users = InMemoryUserRepository()
    return UserService(users), BikeService(InMemoryBikeRepository(), today=_TODAY)


def _create_yz(bikes: BikeService, user, **overrides):
    payload = {
        "nickname": "YZ",
        "make": "Yamaha",
        "model": "YZ250",
        "year": 2006,
        "displacement": 250,
        "bike_type": "dirt_bike",
        "stroke_type": "2T",
        "purchase_date": date(2020, 6, 1),
        "engine_hours_at_purchase": 12.5,
        "current_engine_hours": 42.7,
        "current_engine_hours_is_estimated": False,
    }
    payload.update(overrides)
    return bikes.create(user, **payload)


def test_create_assigns_owner_from_user_not_client() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_owner")
    bike = _create_yz(bikes, owner)
    assert bike.user_id == owner.id
    assert bike.nickname == "YZ"
    assert bike.stroke_type == "2T"
    assert bike.status == "active"
    assert bike.unit_preference == "imperial"
    assert bike.current_engine_hours == Decimal("42.7")
    assert bike.current_engine_hours_is_estimated is False
    assert bike.selected_garage_scene_id is None


def test_list_and_get_are_owner_scoped() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_owner")
    other = users.create("user_clerk_other")
    owned = _create_yz(bikes, owner)
    _create_yz(bikes, other, nickname="Other")
    listed = bikes.list_for_user(owner)
    assert [bike.id for bike in listed] == [owned.id]
    assert bikes.get(owner, owned.id).nickname == "YZ"
    with pytest.raises(BikeNotFound):
        bikes.get(other, owned.id)
    assert bikes.list_for_user(other)[0].nickname == "Other"


def test_unknown_bike_is_not_found() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_missing")
    with pytest.raises(BikeNotFound):
        bikes.get(owner, uuid4())


def test_update_own_bike_and_archive() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_update")
    bike = _create_yz(bikes, owner)
    updated = bikes.update(
        owner,
        bike.id,
        {"nickname": "Track bike", "status": "archive", "current_engine_hours": 50},
    )
    assert updated.nickname == "Track bike"
    assert updated.status == "archive"
    assert updated.current_engine_hours == Decimal("50.0")
    assert updated.make == "Yamaha"


def test_cannot_update_another_users_bike() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_owner")
    other = users.create("user_clerk_other")
    bike = _create_yz(bikes, owner)
    with pytest.raises(BikeNotFound):
        bikes.update(other, bike.id, {"nickname": "Stolen"})
    assert bikes.get(owner, bike.id).nickname == "YZ"


def test_client_cannot_reassign_owner_on_update() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_owner")
    other = users.create("user_clerk_other")
    bike = _create_yz(bikes, owner)
    with pytest.raises(InvalidBike):
        bikes.update(owner, bike.id, {"user_id": other.id})
    assert bikes.get(owner, bike.id).user_id == owner.id


def test_blank_nickname_and_invalid_enums_are_rejected() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_invalid")
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, nickname="  ")
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, stroke_type="rotary")
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, bike_type="scooter")
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, status="deleted")


def test_hours_year_displacement_and_purchase_date_are_validated() -> None:
    users, bikes = _services()
    owner = users.create("user_clerk_numbers")
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, current_engine_hours=-1)
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, displacement=0)
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, year=1800)
    with pytest.raises(InvalidBike):
        _create_yz(bikes, owner, purchase_date=date(2027, 1, 1))
