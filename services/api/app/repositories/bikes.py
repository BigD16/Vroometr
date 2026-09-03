from typing import Protocol
from uuid import UUID

from app.models.bike import Bike
from sqlalchemy import select
from sqlalchemy.orm import Session


class BikeStore(Protocol):
    def get(self, bike_id: UUID, user_id: UUID) -> Bike | None: ...

    def list_for_user(self, user_id: UUID) -> list[Bike]: ...

    def add(self, bike: Bike) -> Bike: ...

    def save(self, bike: Bike) -> Bike: ...


class BikeRepository:
    """Loads bikes for one owner. Queries always include user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, bike_id: UUID, user_id: UUID) -> Bike | None:
        statement = select(Bike).where(Bike.id == bike_id, Bike.user_id == user_id)
        return self._session.scalars(statement).first()

    def list_for_user(self, user_id: UUID) -> list[Bike]:
        statement = select(Bike).where(Bike.user_id == user_id).order_by(Bike.created_at.asc())
        return list(self._session.scalars(statement).all())

    def add(self, bike: Bike) -> Bike:
        self._session.add(bike)
        self._session.flush()
        return bike

    def save(self, bike: Bike) -> Bike:
        self._session.add(bike)
        self._session.flush()
        return bike
