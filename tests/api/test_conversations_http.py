from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext
from app.deps import (
    get_assistant_turn_service,
    get_conversation_service,
    get_token_verifier,
    get_user_service,
)
from app.main import create_app
from app.services.assistant_turn import AssistantTurnService
from app.services.bikes import BikeService
from app.services.compact_context import CompactContextService
from app.services.hierarchical_memory import HierarchicalMemoryService
from app.services.reasoning_agent import ReasoningAgent
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_conversations import setup_conversations
from tests.unit.test_reasoning_agent import ScriptedChat

from vroometr.ai.ports import ChatCompletionTurn


def test_conversation_routes_enforce_ownership_and_boundaries():
    owner, other, bike, second, _, _, service = setup_conversations()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users = InMemoryUserRepository()
    users.add(owner)
    users.add(other)
    bikes = service._bikes  # type: ignore[attr-defined]
    compact = CompactContextService(service, bikes)
    agent = ReasoningAgent(
        ScriptedChat([ChatCompletionTurn(content="I need a cited manual passage for that.")]),
        ToolRegistry(),
        compact,
    )

    def turns():
        def factory(user, *, conversation_id=None, bike_id=None):
            return ToolContext(
                user=user,
                bikes=BikeService(bikes),
                conversations=service,
                compact_context=compact,
                memory=HierarchicalMemoryService(service, bikes),
                conversation_id=conversation_id,
                bike_id=bike_id,
            )

        return AssistantTurnService(service, agent, factory)

    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_assistant_turn_service] = turns
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
    payload = message.json()
    assert payload["message"]["bike_context_id"] == str(bike.id)
    assert payload["assistant_status"] == "ok"
    assert payload["assistant_message"]["role"] == "assistant"
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
    switched_payload = switched.json()
    assert switched_payload["conversation"]["current_bike_id"] == str(second.id)
    assert len(switched_payload["boundaries"]) == 1
    assert client.post(
        f"{path}/bike",
        json={"bike_id": str(second.id)},
        headers=_auth("other-token"),
    ).status_code == 404

    detail = client.get(path, headers=_auth()).json()
    assert "user: torque spec?" in (detail["conversation"]["rolling_summary"] or "")
    assert client.delete(path, headers=_auth("other-token")).status_code == 404
    assert client.delete(path, headers=_auth()).status_code == 204
    assert client.get(path, headers=_auth()).status_code == 404
