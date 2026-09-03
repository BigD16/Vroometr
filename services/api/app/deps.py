from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth.tokens import ClerkJwtVerifier, InvalidIdentity, TokenVerifier
from app.auth.webhooks import ClerkWebhookVerifier, WebhookVerifier
from app.config import settings
from app.db import SessionLocal
from app.errors import AppError
from app.models.user import User
from app.repositories.bikes import BikeRepository
from app.repositories.parental_consents import ParentalConsentRepository
from app.repositories.users import UserRepository
from app.services.age_gate import AgeGateService
from app.services.bikes import BikeService
from app.services.users import UserService


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifier:
    return ClerkJwtVerifier(settings.clerk_jwks_url, settings.clerk_authorized_party)


@lru_cache(maxsize=1)
def get_clerk_webhook_verifier() -> WebhookVerifier:
    return ClerkWebhookVerifier(settings.clerk_webhook_secret)


def get_user_service(session: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(session))


def get_age_gate_service(session: Session = Depends(get_db)) -> AgeGateService:
    return AgeGateService(UserRepository(session), ParentalConsentRepository(session))


def get_bike_service(session: Session = Depends(get_db)) -> BikeService:
    return BikeService(BikeRepository(session))


def require_clerk_user_id(
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise AppError("unauthenticated", "Sign in required", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError("unauthenticated", "Sign in required", status_code=401)
    try:
        return verifier.clerk_user_id(token)
    except InvalidIdentity as exc:
        raise AppError("unauthenticated", "Sign in required", status_code=401) from exc


def get_current_user(
    clerk_user_id: Annotated[str, Depends(require_clerk_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return user_service.ensure(clerk_user_id)
