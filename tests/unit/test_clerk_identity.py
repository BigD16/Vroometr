import pytest
from app.auth.tokens import InvalidIdentity, clerk_user_id_from_claims, issuer_from_jwks_url
from app.services.clerk_sync import ClerkSyncService
from app.services.users import UserService
from tests.unit.fakes import InMemoryUserRepository


def test_claims_use_sub_and_ignore_role_fields() -> None:
    clerk_user_id = clerk_user_id_from_claims(
        {
            "sub": "user_clerk_1",
            "azp": "http://localhost:3000",
            "role": "admin",
            "org_role": "org:admin",
            "public_metadata": {"entitlement": "pro"},
        },
        authorized_party="http://localhost:3000",
    )
    assert clerk_user_id == "user_clerk_1"


def test_claims_reject_wrong_authorized_party() -> None:
    with pytest.raises(InvalidIdentity):
        clerk_user_id_from_claims(
            {"sub": "user_clerk_1", "azp": "https://evil.example"},
            authorized_party="http://localhost:3000",
        )


def test_claims_reject_missing_sub() -> None:
    with pytest.raises(InvalidIdentity):
        clerk_user_id_from_claims({"azp": "http://localhost:3000"}, authorized_party="")


def test_issuer_is_derived_from_jwks_url() -> None:
    assert (
        issuer_from_jwks_url("https://example.clerk.accounts.dev/.well-known/jwks.json")
        == "https://example.clerk.accounts.dev"
    )


def test_webhook_user_created_does_not_copy_clerk_role() -> None:
    service = UserService(InMemoryUserRepository())
    user = ClerkSyncService(service).apply("user.created", "user_clerk_webhook")
    assert user is not None
    assert user.role == "user"
    assert user.entitlement == "none"


def test_webhook_unknown_event_is_ignored() -> None:
    service = UserService(InMemoryUserRepository())
    assert ClerkSyncService(service).apply("session.created", "user_clerk_webhook") is None
    assert service.get_by_clerk_user_id("user_clerk_webhook") is None
