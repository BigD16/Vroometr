from app.main import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_live_does_not_need_other_services() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
