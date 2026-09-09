from app.auth.tokens import InvalidIdentity
from app.deps import (
    get_active_bike_service,
    get_bike_service,
    get_token_verifier,
    get_user_service,
)
from app.main import create_app
from app.services.active_bikes import ActiveBikeService
from app.services.bikes import BikeService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.unit.fakes import InMemoryBikeRepository, InMemoryUserRepository

_YZ = {
    "nickname": "YZ",
    "make": "Yamaha",
    "model": "YZ250",
    "year": 2006,
    "displacement": 250,
    "bike_type": "dirt_bike",
    "stroke_type": "2T",
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
    bikes = InMemoryBikeRepository()
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_bike_service] = lambda: BikeService(bikes)
    app.dependency_overrides[get_active_bike_service] = lambda: ActiveBikeService(users, bikes)
    return TestClient(app)


def _auth(token: str = "good-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_active_bike_requires_sign_in() -> None:
    client = _client()
    assert client.get("/v1/me/active-bike").status_code == 401
    assert (
        client.put(
            "/v1/me/active-bike",
            json={"bike_id": "00000000-0000-0000-0000-000000000001"},
        ).status_code
        == 401
    )


def test_no_bikes_has_no_active_bike() -> None:
    response = _client().get("/v1/me/active-bike", headers=_auth())
    assert response.status_code == 200
    assert response.json() == {"active_bike_id": None}


def test_first_bike_is_default_and_rider_can_select_another() -> None:
    client = _client()
    first = client.post("/v1/bikes", json=_YZ, headers=_auth()).json()
    second = client.post(
        "/v1/bikes",
        json={**_YZ, "nickname": "WR", "model": "WR450F", "stroke_type": "4T"},
        headers=_auth(),
    ).json()
    resolved = client.get("/v1/me/active-bike", headers=_auth())
    assert resolved.json() == {"active_bike_id": first["id"]}
    selected = client.put(
        "/v1/me/active-bike",
        json={
            "bike_id": second["id"],
            "user_id": "00000000-0000-0000-0000-000000000099",
        },
        headers=_auth(),
    )
    assert selected.status_code == 200
    assert selected.json() == {"active_bike_id": second["id"]}


def test_rider_cannot_select_another_users_bike() -> None:
    client = _client()
    foreign = client.post("/v1/bikes", json=_YZ, headers=_auth("other-token")).json()
    response = client.put(
        "/v1/me/active-bike",
        json={"bike_id": foreign["id"]},
        headers=_auth(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_archived_active_bike_falls_back() -> None:
    client = _client()
    first = client.post("/v1/bikes", json=_YZ, headers=_auth()).json()
    second = client.post(
        "/v1/bikes",
        json={**_YZ, "nickname": "Second"},
        headers=_auth(),
    ).json()
    client.get("/v1/me/active-bike", headers=_auth())
    archived = client.patch(
        f"/v1/bikes/{first['id']}",
        json={"status": "archive"},
        headers=_auth(),
    )
    assert archived.status_code == 200
    resolved = client.get("/v1/me/active-bike", headers=_auth())
    assert resolved.json() == {"active_bike_id": second["id"]}
    rejected = client.put(
        "/v1/me/active-bike",
        json={"bike_id": first["id"]},
        headers=_auth(),
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "invalid_active_bike"
