from datetime import UTC, datetime
from uuid import UUID

from app.models.bike import Bike, BikeStatus
from app.models.user import User
from app.repositories.bikes import BikeStore
from app.repositories.users import UserStore


class ActiveBikeNotFound(LookupError):
    """The requested bike does not belong to the signed-in user."""


class ArchivedBikeCannotBeActive(ValueError):
    """Archived bikes cannot be selected as active context."""


class ActiveBikeService:
    """Resolve and persist one owner-validated active bike per user."""

    def __init__(self, users: UserStore, bikes: BikeStore) -> None:
        self._users = users
        self._bikes = bikes

    def resolve(self, user: User) -> Bike | None:
        if user.active_bike_id is not None:
            selected = self._bikes.get(user.active_bike_id, user.id)
            if selected is not None and selected.status != BikeStatus.ARCHIVE.value:
                return selected

        fallback = next(
            (
                bike
                for bike in self._bikes.list_for_user(user.id)
                if bike.status != BikeStatus.ARCHIVE.value
            ),
            None,
        )
        self._persist(user, fallback.id if fallback is not None else None)
        return fallback

    def select(self, user: User, bike_id: UUID) -> Bike:
        bike = self._bikes.get(bike_id, user.id)
        if bike is None:
            raise ActiveBikeNotFound
        if bike.status == BikeStatus.ARCHIVE.value:
            raise ArchivedBikeCannotBeActive
        self._persist(user, bike.id)
        return bike

    def _persist(self, user: User, bike_id: UUID | None) -> None:
        if user.active_bike_id == bike_id:
            return
        user.active_bike_id = bike_id
        user.updated_at = datetime.now(UTC)
        self._users.save(user)
