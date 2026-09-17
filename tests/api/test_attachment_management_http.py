from uuid import uuid4

import pytest
from app.deps import (
    get_attachment_service,
    get_storage_quota_service,
    get_token_verifier,
    get_user_service,
)
from app.main import create_app
from app.services.storage_quota import StorageQuotaService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_attachment_management import make_management


@pytest.fixture
def client_setup():
    owner, other, attachments, _, bike, _, storage, file, service, _ = make_management()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users = InMemoryUserRepository()
    users.add(owner)
    users.add(other)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_attachment_service] = lambda: service
    app.dependency_overrides[get_storage_quota_service] = lambda: StorageQuotaService(attachments)
    return TestClient(app), file, bike, storage


def test_management_routes_require_auth(client_setup):
    client, file, _, _ = client_setup
    for path in ["/v1/attachments", "/v1/storage", f"/v1/attachments/{file.id}/access"]:
        assert client.get(path).status_code == 401
    assert (
        client.request("DELETE", f"/v1/attachments/{file.id}", json={"confirmed": True}).status_code
        == 401
    )


def test_list_and_usage_are_owner_scoped_and_do_not_expose_storage_keys(client_setup):
    client, file, bike, _ = client_setup
    response = client.get("/v1/attachments", headers=_auth())
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(file.id)
    assert "s3_key" not in response.text
    assert client.get("/v1/attachments", headers=_auth("other-token")).json() == []
    assert (
        client.get(f"/v1/attachments?bike_id={bike.id}", headers=_auth("other-token")).status_code
        == 404
    )
    assert client.get("/v1/storage", headers=_auth()).json()["used_bytes"] == 128
    assert client.get("/v1/storage", headers=_auth("other-token")).json()["used_bytes"] == 0


def test_access_is_private_and_pending_files_are_rejected(client_setup):
    client, file, _, _ = client_setup
    path = f"/v1/attachments/{file.id}/access"
    assert client.get(path, headers=_auth("other-token")).status_code == 404
    response = client.get(path, headers=_auth())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    file.status = "pending"
    assert client.get(path, headers=_auth()).status_code == 409


def test_delete_checks_confirmation_storage_failure_and_returns_empty_response(client_setup):
    client, file, _, storage = client_setup
    path = f"/v1/attachments/{file.id}"

    def remove(body, token="good-token"):
        return client.request("DELETE", path, json=body, headers=_auth(token))

    assert remove({"confirmed": True}, "other-token").status_code == 404
    assert remove({"confirmed": False}).status_code == 409
    assert remove({"confirmed": "yes"}).status_code == 422
    assert remove({"confirmed": True, "user_id": str(uuid4())}).status_code == 422
    storage.fail_delete = True
    assert remove({"confirmed": True}).status_code == 503
    storage.fail_delete = False
    response = remove({"confirmed": True})
    assert response.status_code == 204
    assert response.content == b""


def test_infected_file_access_is_blocked_server_side(client_setup):
    from app.models.attachment_processing import AttachmentProcessing

    client, file, _, storage = client_setup
    file.processing = AttachmentProcessing(scan_status="infected")
    for download in ["true", "false"]:
        response = client.get(
            f"/v1/attachments/{file.id}/access?download={download}", headers=_auth()
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "file_blocked"
    assert not storage.reads
