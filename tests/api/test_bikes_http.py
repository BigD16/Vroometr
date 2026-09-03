from datetime import date

from app.auth.tokens import InvalidIdentity
from app.deps import get_bike_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.bikes import BikeService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.unit.fakes import InMemoryBikeRepository, InMemoryUserRepository

_TODAY = date(2026, 9, 3)
_YZ = {
    "nickname": "YZ",
    "make": "Yamaha",
    "model": "YZ250",
    "year": 2006,
    "displacement": 250,
    "bike_type": "dirt_bike",
    "stroke_type": "2T",
    "purchase_date": "2020-06-01",
    "engine_hours_at_purchase": 12.5,
    "current_engine_hours": 42.7,
    "current_engine_hours_is_estimated": False,
}


class _FakeTokens:
    def clerk_user_id(self, token: str) -> str:
        if token == "good-token":
            return "user_clerk_session"
        if token == "other-token":
            return "user_clerk_other"
        raise InvalidIdentity("bad token")


def _client() -> TestClient:
    users = InMemoryUserRepository()
    user_service = UserService(users)
    bike_service = BikeService(InMemoryBikeRepository(), today=_TODAY)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_bike_service] = lambda: bike_service
    return TestClient(app)


def _auth(token: str = "good-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_bikes_require_sign_in() -> None:
    client = _client()
    assert client.get("/v1/bikes").status_code == 401
    assert client.post("/v1/bikes", json=_YZ).status_code == 401


def test_create_list_get_round_trip_ignores_client_owner_id() -> None:
    client = _client()
    created = client.post(
        "/v1/bikes",
        json={**_YZ, "user_id": "00000000-0000-0000-0000-000000000099", "vin": "secret"},
        headers=_auth(),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["nickname"] == "YZ"
    assert body["stroke_type"] == "2T"
    assert body["current_engine_hours"] == 42.7
    assert body["selected_garage_scene_id"] is None
    me = client.get("/v1/me", headers=_auth())
    assert body["user_id"] == me.json()["id"]
    listed = client.get("/v1/bikes", headers=_auth())
    assert listed.status_code == 200
    assert [bike["id"] for bike in listed.json()] == [body["id"]]
    fetched = client.get(f"/v1/bikes/{body['id']}", headers=_auth())
    assert fetched.status_code == 200
    assert fetched.json()["model"] == "YZ250"


def test_another_user_cannot_read_or_update_a_bike() -> None:
    client = _client()
    created = client.post("/v1/bikes", json=_YZ, headers=_auth())
    bike_id = created.json()["id"]
    other_list = client.get("/v1/bikes", headers=_auth("other-token"))
    assert other_list.status_code == 200
    assert other_list.json() == []
    hidden = client.get(f"/v1/bikes/{bike_id}", headers=_auth("other-token"))
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "not_found"
    stolen = client.patch(
        f"/v1/bikes/{bike_id}",
        json={"nickname": "Stolen", "user_id": "00000000-0000-0000-0000-000000000099"},
        headers=_auth("other-token"),
    )
    assert stolen.status_code == 404


def test_owner_can_patch_hours_and_archive() -> None:
    client = _client()
    created = client.post("/v1/bikes", json=_YZ, headers=_auth())
    bike_id = created.json()["id"]
    updated = client.patch(
        f"/v1/bikes/{bike_id}",
        json={"current_engine_hours": 50, "status": "archive"},
        headers=_auth(),
    )
    assert updated.status_code == 200
    assert updated.json()["current_engine_hours"] == 50.0
    assert updated.json()["status"] == "archive"
    assert updated.json()["nickname"] == "YZ"


def test_patch_can_clear_nullable_but_not_required_fields() -> None:
    client = _client()
    created = client.post("/v1/bikes", json=_YZ, headers=_auth())
    bike_id = created.json()["id"]
    cleared = client.patch(
        f"/v1/bikes/{bike_id}",
        json={"purchase_date": None},
        headers=_auth(),
    )
    assert cleared.status_code == 200
    assert cleared.json()["purchase_date"] is None
    rejected = client.patch(
        f"/v1/bikes/{bike_id}",
        json={"nickname": None},
        headers=_auth(),
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "invalid_bike"


def test_invalid_bike_payload_is_400() -> None:
    client = _client()
    response = client.post(
        "/v1/bikes",
        json={**_YZ, "stroke_type": "rotary", "current_engine_hours": -1},
        headers=_auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_bike"
