from datetime import UTC, datetime
from uuid import UUID

from app.models.user import Entitlement, Role, User
from app.repositories.users import UserAlreadyExists, UserStore


class InvalidUserAccess(ValueError):
    """Role or entitlement is not a locked V1 value."""


class UserService:
    """Access rules for users. Clerk proves identity; this row owns role and entitlement."""

    def __init__(self, repository: UserStore) -> None:
        self._repository = repository

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._repository.get_by_id(user_id)

    def get_by_clerk_user_id(self, clerk_user_id: str) -> User | None:
        return self._repository.get_by_clerk_user_id(clerk_user_id)

    def ensure(self, clerk_user_id: str) -> User:
        clerk_user_id = clerk_user_id.strip()
        if not clerk_user_id:
            raise InvalidUserAccess("clerk_user_id is required")
        existing = self._repository.get_by_clerk_user_id(clerk_user_id)
        if existing is not None:
            return existing
        try:
            return self.create(clerk_user_id)
        except UserAlreadyExists:
            found = self._repository.get_by_clerk_user_id(clerk_user_id)
            if found is None:
                raise
            return found

    def create(
        self,
        clerk_user_id: str,
        *,
        role: Role = Role.USER,
        entitlement: Entitlement = Entitlement.NONE,
    ) -> User:
        clerk_user_id = clerk_user_id.strip()
        if not clerk_user_id:
            raise InvalidUserAccess("clerk_user_id is required")
        if not isinstance(role, Role):
            raise InvalidUserAccess(f"invalid role: {role}")
        if not isinstance(entitlement, Entitlement):
            raise InvalidUserAccess(f"invalid entitlement: {entitlement}")
        if self._repository.get_by_clerk_user_id(clerk_user_id) is not None:
            raise UserAlreadyExists
        now = datetime.now(UTC)
        user = User(
            clerk_user_id=clerk_user_id,
            role=role.value,
            entitlement=entitlement.value,
            created_at=now,
            updated_at=now,
        )
        return self._repository.add(user)
