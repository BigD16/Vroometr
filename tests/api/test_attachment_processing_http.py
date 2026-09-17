from app.deps import get_attachment_processing_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_attachment_processing import setup_processing


def test_processing_endpoint_authorizes_rejects_pending_and_prevents_duplicate_retry():
    owner, file, _, jobs, service = setup_processing()
    owner.clerk_user_id = "user_clerk_upload"
    users = InMemoryUserRepository()
    users.add(owner)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_attachment_processing_service] = lambda: service
    client = TestClient(app)
    path = f"/v1/attachments/{file.id}/processing"
    assert client.post(path).status_code == 401
    assert client.post(path, headers=_auth("other-token")).status_code == 404
    file.status = "pending"
    assert client.post(path, headers=_auth()).status_code == 409
    file.status = "uploaded"
    response = client.post(path, headers=_auth())
    assert response.status_code == 202
    assert response.json()["state"] == "queued"
    assert response.json()["scan_status"] == "not_scanned"
    assert response.json()["retry_after"] is not None
    assert client.post(path, headers=_auth()).status_code == 409
    assert len(jobs.messages) == 1
