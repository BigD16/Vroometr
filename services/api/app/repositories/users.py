from typing import Protocol
from uuid import UUID

from app.models.user import User
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class UserStore(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...

    def get_by_clerk_user_id(self, clerk_user_id: str) -> User | None: ...

    def add(self, user: User) -> User: ...

    def save(self, user: User) -> User: ...


class UserAlreadyExists(Exception):
    """A users row already exists for this Clerk id."""


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_clerk_user_id(self, clerk_user_id: str) -> User | None:
        statement = select(User).where(User.clerk_user_id == clerk_user_id)
        return self._session.scalars(statement).first()

    def add(self, user: User) -> User:
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise UserAlreadyExists from exc
        return user

    def save(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()
        return user
