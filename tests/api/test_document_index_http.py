from uuid import uuid4

from app.deps import get_current_user
from app.main import create_app
from app.models.user import User
from app.routes.document_index import get_index_service
from app.services.documents import DocumentNotFound
from fastapi.testclient import TestClient


def test_index_api_requires_identity_owner_and_bounds_page_size():
    owner = User(id=uuid4())

    class Service:
        def status(self, user_id, doc_id):
            if user_id != owner.id:
                raise DocumentNotFound
            return None, False, [], []

        def queue(self, user_id, doc_id):
            raise DocumentNotFound

    app = create_app()
    app.dependency_overrides[get_index_service] = Service
    client = TestClient(app)
    path = f"/v1/documents/{uuid4()}/index"
    assert client.get(path).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: User(id=uuid4())
    assert client.get(path).status_code == 404
    assert client.post(path).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: owner
    result = client.get(path)
    assert result.status_code == 200 and result.json()["total_chunks"] == 0
    assert client.get(path + "?limit=101").status_code == 422
    assert client.get(path + "?offset=-1").status_code == 422
