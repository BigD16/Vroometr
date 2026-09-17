from app.deps import get_conversation_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_conversations import setup_conversations


def test_conversation_routes_enforce_ownership_and_boundaries():
    owner, other, bike, second, _, _, service = setup_conversations()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users = InMemoryUserRepository()
    users.add(owner)
    users.add(other)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_conversation_service] = lambda: service
    client = TestClient(app)

    body = {"bike_id": str(bike.id)}
    assert client.post("/v1/conversations", json=body).status_code == 401
    assert (
        client.post("/v1/conversations", json=body, headers=_auth("other-token")).status_code
        == 404
    )
    created = client.post("/v1/conversations", json=body, headers=_auth())
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    path = f"/v1/conversations/{conversation_id}"

    assert client.get(f"/v1/conversations?bike_id={bike.id}", headers=_auth()).status_code == 200
    assert client.get(path, headers=_auth("other-token")).status_code == 404

    message = client.post(
        f"{path}/messages",
        json={"content": "torque spec?"},
        headers=_auth(),
    )
    assert message.status_code == 201
    assert message.json()["bike_context_id"] == str(bike.id)
    assert (
        client.post(f"{path}/messages", json={"content": " "}, headers=_auth()).status_code
        == 400
    )

    switched = client.post(
        f"{path}/bike",
        json={"bike_id": str(second.id)},
        headers=_auth(),
    )
    assert switched.status_code == 200
    payload = switched.json()
    assert payload["conversation"]["current_bike_id"] == str(second.id)
    assert len(payload["boundaries"]) == 1
    assert client.post(
        f"{path}/bike",
        json={"bike_id": str(second.id)},
        headers=_auth("other-token"),
    ).status_code == 404

    detail = client.get(path, headers=_auth()).json()
    assert detail["conversation"]["rolling_summary"] == "user: torque spec?"
    assert client.delete(path, headers=_auth("other-token")).status_code == 404
    assert client.delete(path, headers=_auth()).status_code == 204
    assert client.get(path, headers=_auth()).status_code == 404
