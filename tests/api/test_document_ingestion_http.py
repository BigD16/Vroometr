from app.deps import get_current_user
from app.main import create_app
from app.routes.document_ingestion import get_ingestion_service
from fastapi.testclient import TestClient
from tests.unit.test_document_ingestion import setup_ingestion
from tests.unit.test_documents import META


def test_ingestion_api_owner_confirmation_status_and_busy():
    owner, other, _, doc, documents, service, _ = setup_ingestion()
    app = create_app()
    app.dependency_overrides[get_ingestion_service] = lambda: service
    client = TestClient(app)
    path = f"/v1/documents/{doc.id}/ingestion"
    assert client.get(path).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: other
    assert client.get(path).status_code == 404
    assert client.post(path).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: owner
    assert client.post(path).status_code == 400
    assert client.get(path).json() == {"ingestion": None, "pages": []}
    documents.confirm(owner, doc.id, META)
    assert client.post(path).status_code == 202
    assert client.post(path).status_code == 409
    assert client.get(path).json()["ingestion"]["state"] == "queued"
