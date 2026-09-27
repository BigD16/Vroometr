from datetime import date

from app.deps import (
    get_bike_service,
    get_maintenance_service,
    get_token_verifier,
    get_user_service,
)
from app.main import create_app
from app.services.bikes import BikeService
from app.services.maintenance import MaintenanceService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.api.test_bikes_http import _YZ, _FakeTokens
from tests.api.test_uploads_http import _auth
from tests.unit.fakes import InMemoryBikeRepository, InMemoryUserRepository
from tests.unit.test_maintenance import MemoryStore


def _client():
    users = InMemoryUserRepository()
    user_service = UserService(users)
    bikes = InMemoryBikeRepository()
    bike_service = BikeService(bikes, today=date(2026, 9, 3))
    maintenance = MaintenanceService(MemoryStore(bikes), bikes)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_bike_service] = lambda: bike_service
    app.dependency_overrides[get_maintenance_service] = lambda: maintenance
    return TestClient(app), bike_service, maintenance


def test_maintenance_taxonomy_and_crud():
    client, bikes, _ = _client()
    created = client.post("/v1/bikes", json=_YZ, headers=_auth())
    assert created.status_code == 200
    bike_id = created.json()["id"]

    tax = client.get("/v1/maintenance/taxonomy", headers=_auth())
    assert tax.status_code == 200
    assert any(item["key"] == "engine" for item in tax.json()["systems"])

    body = {
        "bike_id": bike_id,
        "service_date": "2026-09-01",
        "system": "engine",
        "component": "engine_oil",
        "action": "replace",
        "reason": "scheduled",
        "performer_type": "owner",
        "engine_hours": 42.5,
    }
    saved = client.post("/v1/maintenance", json=body, headers=_auth())
    assert saved.status_code == 201
    record_id = saved.json()["id"]
    assert saved.json()["component"] == "engine_oil"
    assert "next_due" not in saved.json()

    listed = client.get(f"/v1/maintenance?bike_id={bike_id}", headers=_auth())
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    foreign = client.get(
        f"/v1/maintenance/{record_id}", headers=_auth("other-token")
    )
    assert foreign.status_code == 404
    assert client.delete(f"/v1/maintenance/{record_id}", headers=_auth()).status_code == 204
    assert client.get(f"/v1/maintenance?bike_id={bike_id}", headers=_auth()).json() == []


def test_maintenance_rejects_unknown_component():
    client, _, _ = _client()
    created = client.post("/v1/bikes", json=_YZ, headers=_auth())
    assert created.status_code == 200
    bike_id = created.json()["id"]
    bad = client.post(
        "/v1/maintenance",
        json={
            "bike_id": bike_id,
            "service_date": "2026-09-01",
            "system": "engine",
            "component": "not_a_component",
            "action": "replace",
            "reason": "scheduled",
            "performer_type": "owner",
        },
        headers=_auth(),
    )
    assert bad.status_code == 400
