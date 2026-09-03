import json
from base64 import b64encode
from datetime import UTC, datetime

import pytest
from app.auth.webhooks import ClerkWebhookVerifier, InvalidWebhook
from app.deps import get_clerk_webhook_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from svix.webhooks import Webhook
from tests.unit.fakes import InMemoryUserRepository

_SECRET = "whsec_" + b64encode(b"vroometr-test-webhook-secret").decode()


class _FakeWebhook:
    def __init__(self, event: dict) -> None:
        self._event = event

    def verify(self, _payload: bytes, _headers: dict[str, str]) -> dict:
        return self._event


def _app_with_users(event: dict) -> tuple[TestClient, UserService]:
    service = UserService(InMemoryUserRepository())
    app = create_app()
    app.dependency_overrides[get_clerk_webhook_verifier] = lambda: _FakeWebhook(event)
    app.dependency_overrides[get_user_service] = lambda: service
    return TestClient(app), service


def test_clerk_webhook_rejects_bad_signature() -> None:
    app = create_app()
    app.dependency_overrides[get_clerk_webhook_verifier] = lambda: ClerkWebhookVerifier(
        _SECRET
    )
    app.dependency_overrides[get_user_service] = lambda: UserService(
        InMemoryUserRepository()
    )
    response = TestClient(app).post(
        "/v1/webhooks/clerk",
        content=b'{"type":"user.created","data":{"id":"user_1"}}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"


def test_clerk_webhook_accepts_signed_user_created() -> None:
    payload = json.dumps(
        {
            "type": "user.created",
            "data": {
                "id": "user_clerk_signed",
                "public_metadata": {"role": "admin", "entitlement": "pro"},
            },
        }
    )
    timestamp = datetime.now(UTC)
    msg_id = "msg_test_1"
    signature = Webhook(_SECRET).sign(msg_id, timestamp, payload)
    verifier = ClerkWebhookVerifier(_SECRET)
    event = verifier.verify(
        payload.encode(),
        {
            "svix-id": msg_id,
            "svix-timestamp": str(int(timestamp.timestamp())),
            "svix-signature": signature,
        },
    )
    assert event["data"]["id"] == "user_clerk_signed"


def test_signed_webhook_with_wrong_secret_is_rejected() -> None:
    verifier = ClerkWebhookVerifier(_SECRET)
    with pytest.raises(InvalidWebhook):
        verifier.verify(b'{"type":"user.created"}', {})


def test_user_created_webhook_stores_default_access() -> None:
    client, service = _app_with_users(
        {
            "type": "user.created",
            "data": {
                "id": "user_clerk_hook",
                "public_metadata": {"role": "admin"},
            },
        }
    )
    response = client.post("/v1/webhooks/clerk", json={"ignored": True})
    assert response.status_code == 200
    user = service.get_by_clerk_user_id("user_clerk_hook")
    assert user is not None
    assert user.role == "user"
    assert user.entitlement == "none"


def test_unknown_clerk_event_is_ok_and_does_not_create_a_user() -> None:
    client, service = _app_with_users(
        {"type": "session.created", "data": {"id": "sess_1", "user_id": "user_x"}}
    )
    response = client.post("/v1/webhooks/clerk", json={})
    assert response.status_code == 200
    assert service.get_by_clerk_user_id("user_x") is None
    assert service.get_by_clerk_user_id("sess_1") is None
