from app.deps import (
    get_compact_context_service,
    get_conversation_service,
    get_token_verifier,
    get_user_service,
)
from app.main import create_app
from app.services.compact_context import CompactContextService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_compact_context import setup_context


def test_compact_context_route_returns_pack_and_enforces_ownership():
    owner, other, bike, _, _, conversations, _, _, bikes = setup_context()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users = InMemoryUserRepository()
    users.add(owner)
    users.add(other)
    context = CompactContextService(conversations, bikes)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_conversation_service] = lambda: conversations
    app.dependency_overrides[get_compact_context_service] = lambda: context
    client = TestClient(app)

    created = client.post(
        "/v1/conversations",
        json={"bike_id": str(bike.id)},
        headers=_auth(),
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert (
        client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"content": "oil capacity?"},
            headers=_auth(),
        ).status_code
        == 201
    )

    path = f"/v1/conversations/{conversation_id}/context"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=_auth("other-token")).status_code == 404
    response = client.get(path, headers=_auth())
    assert response.status_code == 200
    body = response.json()
    assert body["bike"]["nickname"] == "Trail"
    assert body["conversation"]["recent_turns"][0]["content"] == "oil capacity?"
    assert body["modifications"]["available"] is False
    assert body["maintenance"]["reason"] == "domain_not_implemented"
    assert body["ride"]["available"] is False
    assert body["budget"]["recent_turns_included"] == 1
