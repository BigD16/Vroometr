from uuid import UUID, uuid4

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
