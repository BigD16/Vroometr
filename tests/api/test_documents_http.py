from app.deps import get_document_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_uploads_http import _auth, _FakeTokens
from tests.unit.fakes import InMemoryUserRepository
from tests.unit.test_documents import setup_documents


def test_document_routes_enforce_ownership_and_confirmation():
    owner, other, bike, _, file, _, _, _, service = setup_documents()
    owner.clerk_user_id = "user_clerk_upload"
    other.clerk_user_id = "user_clerk_upload_other"
    users = InMemoryUserRepository()
    users.add(owner)
    users.add(other)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_document_service] = lambda: service
    client = TestClient(app)
    body = dict(
        bike_id=str(bike.id),
        attachment_id=str(file.id),
        document_type="manufacturer_manual",
        make="Test",
        model="Test",
        year=2024,
    )
    assert client.post("/v1/documents", json=body).status_code == 401
    assert client.post("/v1/documents", json=body, headers=_auth("other-token")).status_code == 404
    response = client.post("/v1/documents", json=body, headers=_auth())
    assert response.status_code == 201
    document = response.json()["document"]
    assert document["status"] == "awaiting_confirmation"
    path = f"/v1/documents/{document['id']}"
    assert client.put(f"{path}/primary", headers=_auth()).status_code == 400
    metadata = {key: body[key] for key in ("document_type", "make", "model", "year")}
    assert (
        client.post(f"{path}/confirm", json=metadata, headers=_auth("other-token")).status_code
        == 404
    )
    assert (
        client.post(f"{path}/confirm", json=metadata, headers=_auth()).json()["is_primary"] is True
    )
    assert client.get(f"/v1/documents?bike_id={bike.id}", headers=_auth()).status_code == 200
