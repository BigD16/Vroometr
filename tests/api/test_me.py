from app.auth.tokens import InvalidIdentity
from app.deps import get_token_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.unit.fakes import InMemoryUserRepository


class _FakeTokens:
    def clerk_user_id(self, token: str) -> str:
        if token == "good-token":
            return "user_clerk_session"
        raise InvalidIdentity("bad token")


def _client() -> tuple[TestClient, UserService]:
    service = UserService(InMemoryUserRepository())
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: service
    return TestClient(app), service


def test_me_requires_a_bearer_token() -> None:
    client, _service = _client()
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_me_rejects_a_bad_token() -> None:
    client, _service = _client()
    response = client.get("/v1/me", headers={"Authorization": "Bearer no-good"})
    assert response.status_code == 401


def test_me_returns_database_role_not_request_headers() -> None:
    client, service = _client()
    response = client.get(
        "/v1/me",
        headers={
            "Authorization": "Bearer good-token",
            "X-User-Id": "someone-else",
            "X-Role": "admin",
            "X-Entitlement": "pro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["clerk_user_id"] == "user_clerk_session"
    assert body["role"] == "user"
    assert body["entitlement"] == "none"
    stored = service.get_by_clerk_user_id("user_clerk_session")
    assert stored is not None
    assert stored.role == "user"
    assert stored.entitlement == "none"
