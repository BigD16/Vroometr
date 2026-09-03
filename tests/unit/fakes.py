from uuid import UUID, uuid4

from app.models.bike import Bike
from app.models.parental_consent import ParentalConsent
from app.models.user import User
from app.repositories.users import UserAlreadyExists


class InMemoryUserRepository:
    """Test double. Does not talk to Postgres."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}
        self._by_clerk: dict[str, User] = {}

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    def get_by_clerk_user_id(self, clerk_user_id: str) -> User | None:
        return self._by_clerk.get(clerk_user_id)

    def add(self, user: User) -> User:
        if user.clerk_user_id in self._by_clerk:
            raise UserAlreadyExists
        if user.id is None:
            user.id = uuid4()
        self._by_id[user.id] = user
        self._by_clerk[user.clerk_user_id] = user
        return user

    def save(self, user: User) -> User:
        self._by_id[user.id] = user
        self._by_clerk[user.clerk_user_id] = user
        return user


class InMemoryParentalConsentRepository:
    def __init__(self) -> None:
        self._items: list[ParentalConsent] = []

    def add(self, consent: ParentalConsent) -> ParentalConsent:
        if consent.id is None:
            consent.id = uuid4()
        self._items.append(consent)
        return consent

    def latest_for_minor(self, minor_user_id: UUID) -> ParentalConsent | None:
        matches = [item for item in self._items if item.minor_user_id == minor_user_id]
        if not matches:
            return None
        return max(matches, key=lambda item: item.created_at)


class InMemoryBikeRepository:
    """Test double. get/list never return another user's bike."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Bike] = {}

    def get(self, bike_id: UUID, user_id: UUID) -> Bike | None:
        bike = self._by_id.get(bike_id)
        if bike is None or bike.user_id != user_id:
            return None
        return bike

    def list_for_user(self, user_id: UUID) -> list[Bike]:
        owned = [bike for bike in self._by_id.values() if bike.user_id == user_id]
        return sorted(owned, key=lambda bike: bike.created_at)

    def add(self, bike: Bike) -> Bike:
        if bike.id is None:
            bike.id = uuid4()
        self._by_id[bike.id] = bike
        return bike

    def save(self, bike: Bike) -> Bike:
        self._by_id[bike.id] = bike
        return bike
