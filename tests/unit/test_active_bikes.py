from datetime import date

import pytest
from app.services.active_bikes import (
    ActiveBikeNotFound,
    ActiveBikeService,
    ArchivedBikeCannotBeActive,
)
from app.services.bikes import BikePatch, BikeService
from app.services.users import UserService
from tests.unit.fakes import InMemoryBikeRepository, InMemoryUserRepository

_TODAY = date(2026, 9, 8)


def _services() -> tuple[UserService, BikeService, ActiveBikeService]:
    users = InMemoryUserRepository()
    bikes = InMemoryBikeRepository()
    return (
        UserService(users),
        BikeService(bikes, today=_TODAY),
        ActiveBikeService(users, bikes),
    )


def _create_bike(bikes: BikeService, user, nickname: str):
    return bikes.create(
        user,
        nickname=nickname,
        make="Yamaha",
        model="YZ250",
        year=2006,
        displacement=250,
        bike_type="dirt_bike",
        stroke_type="2T",
    )


def test_no_owned_bikes_resolves_to_none() -> None:
    users, _, active_bikes = _services()
    owner = users.create("user_clerk_empty")
    assert active_bikes.resolve(owner) is None
    assert owner.active_bike_id is None


def test_first_owned_bike_is_selected_and_persisted() -> None:
    users, bikes, active_bikes = _services()
    owner = users.create("user_clerk_default")
    first = _create_bike(bikes, owner, "First")
    _create_bike(bikes, owner, "Second")
    assert active_bikes.resolve(owner).id == first.id
    assert owner.active_bike_id == first.id


def test_explicit_selection_is_owner_scoped() -> None:
    users, bikes, active_bikes = _services()
    owner = users.create("user_clerk_owner")
    other = users.create("user_clerk_other")
    owned = _create_bike(bikes, owner, "Owned")
    foreign = _create_bike(bikes, other, "Foreign")
    assert active_bikes.select(owner, owned.id).id == owned.id
    with pytest.raises(ActiveBikeNotFound):
        active_bikes.select(owner, foreign.id)
    assert owner.active_bike_id == owned.id


def test_archived_selection_falls_back_and_cannot_be_reselected() -> None:
    users, bikes, active_bikes = _services()
    owner = users.create("user_clerk_archive")
    first = _create_bike(bikes, owner, "First")
    fallback = _create_bike(bikes, owner, "Fallback")
    active_bikes.select(owner, first.id)
    bikes.update(owner, first.id, BikePatch(status="archive"))
    assert active_bikes.resolve(owner).id == fallback.id
    assert owner.active_bike_id == fallback.id
    with pytest.raises(ArchivedBikeCannotBeActive):
        active_bikes.select(owner, first.id)
