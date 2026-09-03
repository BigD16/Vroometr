from datetime import date

from app.auth.tokens import InvalidIdentity
from app.deps import get_age_gate_service, get_token_verifier, get_user_service
from app.main import create_app
from app.services.age_gate import AgeGateService
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.unit.fakes import InMemoryParentalConsentRepository, InMemoryUserRepository


class _FakeTokens:
    def clerk_user_id(self, token: str) -> str:
        if token == "good-token":
            return "user_clerk_session"
        raise InvalidIdentity("bad token")


def _client() -> TestClient:
    users = InMemoryUserRepository()
    consents = InMemoryParentalConsentRepository()
    user_service = UserService(users)
    age_gate = AgeGateService(users, consents, today=date(2026, 9, 3))
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_age_gate_service] = lambda: age_gate
    return TestClient(app)


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer good-token"}


def test_eligibility_requires_sign_in() -> None:
    assert _client().get("/v1/me/eligibility").status_code == 401


def test_eligibility_is_unknown_until_date_of_birth() -> None:
    client = _client()
    response = client.get("/v1/me/eligibility", headers=_auth())
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
    assert response.json()["date_of_birth"] is None


def test_teen_consent_round_trip_ignores_client_minor_id() -> None:
    client = _client()
    born = client.post(
        "/v1/me/date-of-birth",
        json={"date_of_birth": "2010-06-01"},
        headers=_auth(),
    )
    assert born.status_code == 200
    assert born.json()["status"] == "needs_consent"
    granted = client.post(
        "/v1/parental-consents",
        json={
            "guardian_contact": "parent@example.com",
            "consent_version": "2026-09-01",
            "minor_user_id": "00000000-0000-0000-0000-000000000099",
        },
        headers=_auth(),
    )
    assert granted.status_code == 200
    assert granted.json()["status"] == "granted"
    assert granted.json()["guardian_contact"] == "parent@example.com"
    me = client.get("/v1/me", headers=_auth())
    assert granted.json()["minor_user_id"] == me.json()["id"]
    assert granted.json()["minor_user_id"] != "00000000-0000-0000-0000-000000000099"
    check = client.get("/v1/me/eligibility", headers=_auth())
    assert check.json()["status"] == "consented"


def test_under_13_date_of_birth_is_forbidden() -> None:
    client = _client()
    response = client.post(
        "/v1/me/date-of-birth",
        json={"date_of_birth": "2016-01-01"},
        headers=_auth(),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "underage_blocked"


def test_future_date_of_birth_is_invalid() -> None:
    client = _client()
    response = client.post(
        "/v1/me/date-of-birth",
        json={"date_of_birth": "2027-01-01"},
        headers=_auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_age_gate"


def test_blank_consent_is_invalid() -> None:
    client = _client()
    client.post("/v1/me/date-of-birth", json={"date_of_birth": "2010-06-01"}, headers=_auth())
    response = client.post(
        "/v1/parental-consents",
        json={"guardian_contact": "  ", "consent_version": "2026-09-01"},
        headers=_auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_age_gate"
