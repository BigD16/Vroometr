from app.models.user import User
from app.services.users import UserService

_USER_EVENTS = frozenset({"user.created", "user.updated"})


class ClerkSyncService:
    """Apply Clerk identity events. Never copies role or entitlement from Clerk."""

    def __init__(self, users: UserService) -> None:
        self._users = users

    def apply(self, event_type: str, clerk_user_id: str) -> User | None:
        if event_type not in _USER_EVENTS:
            return None
        return self._users.ensure(clerk_user_id)
