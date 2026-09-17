from uuid import uuid4

import pytest
from app.deps import get_attachment_link_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_attachment_links import make_link_setup


@pytest.fixture
def client_setup():
    service, owner, other, bike, _, foreign, attachment, _ = make_link_setup()
    users = InMemoryUserRepository()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users.add(owner)
    users.add(other)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_attachment_link_service] = lambda: service
    body = dict(attachment_id=str(attachment.id), entity_type="bike", entity_id=str(bike.id))
    return TestClient(app), body, attachment, foreign


def test_link_routes_require_authentication(client_setup):
    client, body, _, _ = client_setup
    assert client.post("/v1/attachment-links", json=body).status_code == 401
    assert client.get("/v1/attachment-links", params=body).status_code == 401
    assert client.delete(f"/v1/attachment-links/{uuid4()}").status_code == 401


def test_link_list_retry_and_unlink(client_setup):
    client, body, _, _ = client_setup
    response = client.post("/v1/attachment-links", json=body, headers=_auth())
    assert response.status_code == 200
    link = response.json()
    assert "s3_key" not in link
    assert link["relationship_type"] == "reference"
    assert client.post("/v1/attachment-links", json=body, headers=_auth()).json() == link
    assert client.get("/v1/attachment-links", params=body, headers=_auth()).json() == [link]
    assert client.delete(f"/v1/attachment-links/{link['id']}", headers=_auth()).status_code == 204
    assert client.get("/v1/attachment-links", params=body, headers=_auth()).json() == []


def test_foreign_ids_are_hidden_on_every_route(client_setup):
    client, body, _, foreign = client_setup
    link = client.post("/v1/attachment-links", json=body, headers=_auth()).json()
    assert (
        client.post("/v1/attachment-links", json=body, headers=_auth("other-token")).status_code
        == 404
    )
    assert (
        client.get("/v1/attachment-links", params=body, headers=_auth("other-token")).status_code
        == 404
    )
    assert (
        client.delete(
            f"/v1/attachment-links/{link['id']}", headers=_auth("other-token")
        ).status_code
        == 404
    )
    foreign_body = body | {"entity_id": str(foreign.id)}
    assert (
        client.post("/v1/attachment-links", json=foreign_body, headers=_auth()).status_code == 404
    )
    assert (
        client.post(
            "/v1/attachment-links", json=foreign_body, headers=_auth("other-token")
        ).status_code
        == 404
    )


def test_validation_and_pending_upload(client_setup):
    client, body, attachment, _ = client_setup
    assert (
        client.post(
            "/v1/attachment-links", json=body | {"entity_type": "modification"}, headers=_auth()
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/v1/attachment-links", json=body | {"user_id": str(uuid4())}, headers=_auth()
        ).status_code
        == 422
    )
    attachment.status = "pending"
    response = client.post("/v1/attachment-links", json=body, headers=_auth())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "upload_incomplete"
